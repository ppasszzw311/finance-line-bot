"""
LINE Flex Message 建構器
產生美觀的卡片式訊息
"""
from typing import List, Dict, Any
from decimal import Decimal
from models.schemas import HoldingResponse, PortfolioSummary, TransactionResponse


class MessageBuilder:
    """LINE Flex Message 建構器"""
    
    @staticmethod
    def portfolio_bubble(portfolio: PortfolioSummary) -> Dict[str, Any]:
        """
        建立投資組合 Flex Message Bubble
        
        Args:
            portfolio: 投資組合資料
            
        Returns:
            Dict: Flex Message bubble JSON
        """
        # 決定顏色（正負）
        pnl_color = "#06c755" if portfolio.total_unrealized_pnl >= 0 else "#ff0000"
        pnl_sign = "+" if portfolio.total_unrealized_pnl >= 0 else ""
        
        # 建立 body contents
        body_contents = [
            {
                "type": "text",
                "text": f"📊 {portfolio.investor_name} 的投資組合",
                "weight": "bold",
                "size": "xl",
                "margin": "md"
            },
            {
                "type": "separator",
                "margin": "md"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    MessageBuilder._info_row("持有股票", f"{portfolio.total_stocks} 支"),
                    MessageBuilder._info_row("總投入", f"${portfolio.total_invested:,.0f}"),
                    MessageBuilder._info_row("目前市值", f"${portfolio.current_value:,.0f}"),
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "未實現損益",
                                "size": "sm",
                                "color": "#555555",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": f"{pnl_sign}${portfolio.total_unrealized_pnl:,.0f} ({pnl_sign}{portfolio.total_unrealized_pnl_pct}%)",
                                "size": "sm",
                                "color": pnl_color,
                                "align": "end",
                                "weight": "bold"
                            }
                        ]
                    }
                ]
            }
        ]
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents
            }
        }
    
    @staticmethod
    def holdings_carousel(holdings: List[HoldingResponse]) -> Dict[str, Any]:
        """
        建立持股列表 Flex Message Carousel
        
        Args:
            holdings: 持股列表
            
        Returns:
            Dict: Flex Message carousel JSON
        """
        bubbles = []
        
        for holding in holdings[:10]:  # 限制最多 10 個 bubble
            bubble = MessageBuilder._holding_bubble(holding)
            bubbles.append(bubble)
        
        return {
            "type": "carousel",
            "contents": bubbles
        }
    
    @staticmethod
    def _holding_bubble(holding: HoldingResponse) -> Dict[str, Any]:
        """建立單支股票的 bubble"""
        stock_display = holding.stock_name or holding.stock_code
        stock_code_short = holding.stock_code.replace('.TW', '')
        
        # 計算顏色
        pnl_color = "#06c755"
        pnl_sign = "+"
        if holding.unrealized_pnl and holding.unrealized_pnl < 0:
            pnl_color = "#ff0000"
            pnl_sign = ""
        
        return {
            "type": "bubble",
            "size": "micro",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": stock_display,
                        "weight": "bold",
                        "size": "sm"
                    },
                    {
                        "type": "text",
                        "text": stock_code_short,
                        "size": "xs",
                        "color": "#aaaaaa"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "spacing": "sm",
                        "contents": [
                            MessageBuilder._info_row_small("持有", f"{holding.total_quantity} 股"),
                            MessageBuilder._info_row_small("成本價", f"${holding.average_cost}"),
                            MessageBuilder._info_row_small(
                                "現價",
                                f"${holding.current_price}" if holding.current_price else "查詢中...",
                                pnl_color if holding.current_price else "#aaaaaa"
                            ),
                        ]
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": "損益",
                                "size": "xs",
                                "color": "#aaaaaa",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": f"{pnl_sign}${holding.unrealized_pnl:,.0f}" if holding.unrealized_pnl else "--",
                                "size": "xs",
                                "color": pnl_color,
                                "align": "end"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": f"{pnl_sign}{holding.unrealized_pnl_pct}%" if holding.unrealized_pnl_pct else "--",
                        "size": "md",
                        "color": pnl_color,
                        "align": "center",
                        "weight": "bold",
                        "margin": "sm"
                    }
                ]
            }
        }
    
    @staticmethod
    def transaction_confirmation(transaction: TransactionResponse, stock_name: str = None) -> Dict[str, Any]:
        """
        建立交易確認 Flex Message
        
        Args:
            transaction: 交易記錄
            stock_name: 股票名稱
            
        Returns:
            Dict: Flex Message bubble JSON
        """
        action = "買入" if transaction.transaction_type == "BUY" else "賣出"
        action_emoji = "📈" if transaction.transaction_type == "BUY" else "📉"
        action_color = "#06c755" if transaction.transaction_type == "BUY" else "#ff6b6b"
        
        stock_display = stock_name or transaction.stock_code
        stock_code_short = transaction.stock_code.replace('.TW', '')
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{action_emoji} 交易記錄成功",
                        "weight": "bold",
                        "size": "lg",
                        "color": action_color
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            MessageBuilder._info_row("投資人", transaction.investor_name),
                            MessageBuilder._info_row("動作", action),
                            MessageBuilder._info_row("股票", f"{stock_display} ({stock_code_short})"),
                            MessageBuilder._info_row("數量", f"{transaction.quantity} 股"),
                            MessageBuilder._info_row("價格", f"${transaction.price_per_share}"),
                            MessageBuilder._info_row("手續費", f"${transaction.transaction_fee}"),
                        ]
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": "總金額",
                                "size": "sm",
                                "weight": "bold"
                            },
                            {
                                "type": "text",
                                "text": f"${transaction.total_amount:,.2f}",
                                "size": "sm",
                                "weight": "bold",
                                "align": "end",
                                "color": action_color
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def comparison_ranking(leaderboard: List[dict]) -> Dict[str, Any]:
        """
        建立績效排行榜 Flex Message
        
        Args:
            leaderboard: 排行榜資料
            
        Returns:
            Dict: Flex Message bubble JSON
        """
        contents = [
            {
                "type": "text",
                "text": "🏆 投資績效排行榜",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "separator",
                "margin": "md"
            }
        ]
        
        for item in leaderboard[:10]:  # 最多顯示前 10 名
            rank = item['rank']
            name = item['name']
            return_pct = item['return_pct']
            item_type = item['type']
            
            # 排名 emoji
            if rank == 1:
                rank_text = "🥇"
            elif rank == 2:
                rank_text = "🥈"
            elif rank == 3:
                rank_text = "🥉"
            else:
                rank_text = f"{rank}."
            
            # 類型 emoji
            type_emoji = "👤" if item_type == "investor" else "📊"
            
            # 顏色
            color = "#06c755" if return_pct >= 0 else "#ff0000"
            sign = "+" if return_pct >= 0 else ""
            
            contents.append({
                "type": "box",
                "layout": "horizontal",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{rank_text} {type_emoji}",
                        "size": "sm",
                        "flex": 0,
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": name,
                        "size": "sm",
                        "flex": 3
                    },
                    {
                        "type": "text",
                        "text": f"{sign}{return_pct:.2f}%",
                        "size": "sm",
                        "color": color,
                        "align": "end",
                        "weight": "bold",
                        "flex": 2
                    }
                ]
            })
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents
            }
        }
    
    @staticmethod
    def _info_row(label: str, value: str, value_color: str = "#111111") -> Dict[str, Any]:
        """建立資訊列（標準尺寸）"""
        return {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "sm",
                    "color": "#555555",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": value,
                    "size": "sm",
                    "color": value_color,
                    "align": "end"
                }
            ]
        }
    
    @staticmethod
    def _info_row_small(label: str, value: str, value_color: str = "#111111") -> Dict[str, Any]:
        """建立資訊列（小尺寸）"""
        return {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "xs",
                    "color": "#aaaaaa",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": value,
                    "size": "xs",
                    "color": value_color,
                    "align": "end"
                }
            ]
        }
    
    @staticmethod
    def help_message() -> str:
        """產生使用說明文字訊息"""
        return """📖 使用說明

📝 記錄交易
直接輸入交易訊息，例如：
• 買 2330 100股 250元
• 我買台積電 50股 @600
• 小明賣鴻海200股 價格120

支援格式：
[投資人] [動作] [股票] [數量]股 [價格]元

💼 查看持股
• 點選「我的持股」查看自己的持股
• 點選「朋友持股」選擇朋友查看

💰 損益報告
• 顯示未實現損益與已實現損益
• 包含詳細的交易歷史

📊 績效比較
• 與朋友比較投資績效
• 與 ETF (0050, 0056, 00878) 比較

❓ 常見問題
Q: 如何記錄朋友的交易？
A: 在訊息開頭加上朋友名字，如「小明買...」

Q: 手續費如何計算？
A: 系統自動計算券商手續費(0.1425%)與證交稅(0.3%)

Q: 股票代碼還是名稱？
A: 兩者都可以，系統會自動轉換"""
