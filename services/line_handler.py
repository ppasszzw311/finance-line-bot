"""
LINE Bot Handler - Webhook 事件處理
"""
import os
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, QuickReply, QuickReplyButton,
    MessageAction, PostbackEvent
)
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from sqlalchemy.orm import Session
from services.message_parser import MessageParser
from services.transaction_service import TransactionService
from services.portfolio_service import PortfolioService
from services.comparison_service import ComparisonService
from services.stock_service import StockService
from utils.message_builder import MessageBuilder
from models.schemas import ParsedTransaction
import logging

logger = logging.getLogger(__name__)

# LINE Bot API 設定
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))


class LineHandler:
    """LINE Bot 事件處理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = MessageParser(db)
        self.transaction_service = TransactionService(db)
        self.portfolio_service = PortfolioService(db)
        self.comparison_service = ComparisonService(db)
        self.stock_service = StockService(db)
        self.message_builder = MessageBuilder()
    
    def handle_text_message(self, event: MessageEvent):
        """
        處理文字訊息
        
        Args:
            event: LINE MessageEvent
        """
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        logger.info(f"Received message from {user_id}: {message_text}")
        
        # 檢查是否為指令
        if message_text.startswith('/') or message_text in ['幫助', '說明', 'help']:
            self._handle_command(event, message_text)
            return
        
        # 嘗試解析為交易訊息
        parsed = self.parser.parse_transaction_message(message_text)
        
        if parsed:
            # 驗證解析結果
            is_valid, error_msg = self.parser.validate_transaction(parsed)
            
            if is_valid:
                # 顯示確認訊息
                confirmation = self.parser.generate_confirmation_message(parsed)
                
                # 使用 Quick Reply 讓用戶確認
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=confirmation,
                        quick_reply=QuickReply(items=[
                            QuickReplyButton(
                                action=MessageAction(label="✅ 確認", text="確認交易")
                            ),
                            QuickReplyButton(
                                action=MessageAction(label="❌ 取消", text="取消")
                            )
                        ])
                    )
                )
                
                # 暫存解析結果（實際應用中可使用 Redis 或資料庫）
                # 這裡簡化處理：直接記錄交易
                try:
                    transaction = self.transaction_service.create_transaction(
                        user_id,
                        parsed
                    )
                    
                    # 取得股票名稱
                    stock_name = self.stock_service.get_stock_name(parsed.stock_code)
                    
                    # 發送成功訊息
                    flex_message = FlexSendMessage(
                        alt_text="交易記錄成功",
                        contents=self.message_builder.transaction_confirmation(
                            transaction,
                            stock_name
                        )
                    )
                    
                    line_bot_api.push_message(user_id, flex_message)
                    
                except Exception as e:
                    logger.error(f"Error creating transaction: {e}")
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"❌ 記錄失敗：{str(e)}")
                    )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ {error_msg}")
                )
        else:
            # 無法解析，提供提示
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="😊 無法識別您的訊息。\n\n" +
                         "請使用以下格式記錄交易：\n" +
                         "• 買 2330 100股 250元\n" +
                         "• 小明賣鴻海200股 價格120\n\n" +
                         "或回覆「說明」查看完整使用指南"
                )
            )
    
    def _handle_command(self, event: MessageEvent, command: str):
        """處理指令訊息"""
        user_id = event.source.user_id
        
        if command in ['幫助', '說明', 'help', '/help']:
            help_text = self.message_builder.help_message()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text)
            )
        
        elif command in ['持股', '我的持股', '/portfolio']:
            self._show_portfolio(event, user_id, "我")
        
        elif command in ['損益', '損益報告', '/pnl']:
            self._show_pnl(event, user_id, "我")
        
        elif command in ['排行', '排行榜', '/ranking']:
            self._show_ranking(event, user_id)
        
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="未知指令，請回覆「說明」查看可用指令")
            )
    
    def _show_portfolio(self, event: MessageEvent, user_id: str, investor_name: str):
        """顯示持股"""
        try:
            portfolio = self.portfolio_service.get_portfolio(user_id, investor_name)
            
            if not portfolio or portfolio.total_stocks == 0:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"📊 {investor_name} 目前沒有持股記錄")
                )
                return
            
            # 發送投資組合總覽
            summary_flex = FlexSendMessage(
                alt_text=f"{investor_name}的投資組合",
                contents=self.message_builder.portfolio_bubble(portfolio)
            )
            
            # 如果有持股，發送持股明細
            if portfolio.holdings:
                holdings_flex = FlexSendMessage(
                    alt_text="持股明細",
                    contents=self.message_builder.holdings_carousel(portfolio.holdings)
                )
                
                line_bot_api.reply_message(
                    event.reply_token,
                    [summary_flex, holdings_flex]
                )
            else:
                line_bot_api.reply_message(event.reply_token, summary_flex)
        
        except Exception as e:
            logger.error(f"Error showing portfolio: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ 查詢失敗：{str(e)}")
            )
    
    def _show_pnl(self, event: MessageEvent, user_id: str, investor_name: str):
        """顯示損益報告"""
        try:
            # 取得未實現損益（從 portfolio）
            portfolio = self.portfolio_service.get_portfolio(user_id, investor_name)
            
            if not portfolio:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"📊 {investor_name} 目前沒有交易記錄")
                )
                return
            
            # 取得已實現損益
            realized_pnl_list = self.portfolio_service.get_realized_pnl(user_id, investor_name)
            
            # 建立報告文字
            report = f"💰 {investor_name} 的損益報告\n\n"
            report += "【未實現損益】\n"
            report += f"總投入：${portfolio.total_invested:,.0f}\n"
            report += f"目前市值：${portfolio.current_value:,.0f}\n"
            
            pnl_sign = "+" if portfolio.total_unrealized_pnl >= 0 else ""
            report += f"損益：{pnl_sign}${portfolio.total_unrealized_pnl:,.0f} ({pnl_sign}{portfolio.total_unrealized_pnl_pct}%)\n"
            
            if realized_pnl_list:
                report += "\n【已實現損益】\n"
                total_realized = sum(r.realized_pnl for r in realized_pnl_list)
                
                for r in realized_pnl_list:
                    sign = "+" if r.realized_pnl >= 0 else ""
                    report += f"{r.stock_name}: {sign}${r.realized_pnl:,.0f}\n"
                
                total_sign = "+" if total_realized >= 0 else ""
                report += f"\n總已實現損益：{total_sign}${total_realized:,.0f}"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=report)
            )
        
        except Exception as e:
            logger.error(f"Error showing P&L: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ 查詢失敗：{str(e)}")
            )
    
    def _show_ranking(self, event: MessageEvent, user_id: str):
        """顯示排行榜"""
        try:
            leaderboard = self.comparison_service.get_leaderboard(user_id, include_etfs=True)
            
            if not leaderboard:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="📊 目前沒有可比較的資料")
                )
                return
            
            # 發送排行榜 Flex Message
            ranking_flex = FlexSendMessage(
                alt_text="投資績效排行榜",
                contents=self.message_builder.comparison_ranking(leaderboard)
            )
            
            line_bot_api.reply_message(event.reply_token, ranking_flex)
        
        except Exception as e:
            logger.error(f"Error showing ranking: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ 查詢失敗：{str(e)}")
            )
    
    def handle_follow(self, event):
        """處理用戶加入好友事件"""
        user_id = event.source.user_id
        
        # 取得用戶資料
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
        except LineBotApiError:
            display_name = None
        
        # 建立用戶
        self.transaction_service.get_or_create_line_user(user_id, display_name)
        
        # 發送歡迎訊息
        welcome_text = f"""👋 歡迎使用股票投資記錄 Bot！

我可以幫你記錄：
• 📝 自己與朋友的買賣交易
• 💼 查看持股與即時損益
• 📊 比較投資績效

快速開始：
直接輸入「買 2330 100股 250元」開始記錄！
回覆「說明」查看完整功能

祝投資順利！ 🚀"""
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_text)
        )
        
        logger.info(f"New user followed: {user_id}")
