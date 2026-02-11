"""
投資組合服務：持股查詢、損益計算
"""
from decimal import Decimal
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models.database import LineUser, Investor, Holding, Transaction, TransactionType
from models.schemas import HoldingResponse, PortfolioSummary, RealizedPnL
from services.stock_service import StockService
import logging

logger = logging.getLogger(__name__)


class PortfolioService:
    """投資組合服務"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stock_service = StockService(db)
    
    def get_portfolio(self, line_user_id: str, investor_name: str = "我") -> Optional[PortfolioSummary]:
        """
        取得投資組合總覽
        
        Args:
            line_user_id: LINE 用戶 ID
            investor_name: 投資人名稱
            
        Returns:
            Optional[PortfolioSummary]: 投資組合總覽
        """
        # 取得投資人
        investor = self._get_investor(line_user_id, investor_name)
        if not investor:
            return None
        
        # 取得所有持股
        holdings = self.db.query(Holding).filter(
            Holding.investor_id == investor.id
        ).all()
        
        if not holdings:
            return PortfolioSummary(
                investor_name=investor_name,
                total_stocks=0,
                total_invested=Decimal('0'),
                current_value=Decimal('0'),
                total_unrealized_pnl=Decimal('0'),
                total_unrealized_pnl_pct=Decimal('0'),
                holdings=[]
            )
        
        # 計算每支股票的損益
        holdings_response = []
        total_invested = Decimal('0')
        total_current_value = Decimal('0')
        
        for holding in holdings:
            holding_data = self._calculate_holding_pnl(holding)
            holdings_response.append(holding_data)
            total_invested += holding.total_invested
            if holding_data.current_value:
                total_current_value += holding_data.current_value
        
        # 計算總損益
        total_unrealized_pnl = total_current_value - total_invested
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else Decimal('0')
        
        return PortfolioSummary(
            investor_name=investor_name,
            total_stocks=len(holdings),
            total_invested=total_invested,
            current_value=total_current_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct.quantize(Decimal('0.01')),
            holdings=holdings_response
        )
    
    def _calculate_holding_pnl(self, holding: Holding) -> HoldingResponse:
        """計算單支股票的損益"""
        # 查詢即時股價
        price_info = self.stock_service.get_stock_price(holding.stock_code)
        stock_name = self.stock_service.get_stock_name(holding.stock_code)
        
        current_price = None
        current_value = None
        unrealized_pnl = None
        unrealized_pnl_pct = None
        
        if price_info and price_info.current_price:
            current_price = price_info.current_price
            current_value = current_price * holding.total_quantity
            unrealized_pnl = current_value - holding.total_invested
            unrealized_pnl_pct = (unrealized_pnl / holding.total_invested * 100) if holding.total_invested > 0 else Decimal('0')
        
        return HoldingResponse(
            stock_code=holding.stock_code,
            stock_name=stock_name,
            total_quantity=holding.total_quantity,
            average_cost=holding.average_cost,
            total_invested=holding.total_invested,
            current_price=current_price,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct.quantize(Decimal('0.01')) if unrealized_pnl_pct else None,
            last_updated=holding.last_updated
        )
    
    def get_realized_pnl(
        self,
        line_user_id: str,
        investor_name: str = "我",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[RealizedPnL]:
        """
        計算已實現損益
        
        Args:
            line_user_id: LINE 用戶 ID
            investor_name: 投資人名稱
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            List[RealizedPnL]: 已實現損益列表
        """
        investor = self._get_investor(line_user_id, investor_name)
        if not investor:
            return []
        
        # 查詢賣出交易
        query = self.db.query(Transaction).filter(
            and_(
                Transaction.investor_id == investor.id,
                Transaction.transaction_type == TransactionType.SELL
            )
        )
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        sell_transactions = query.all()
        
        # 依股票分組計算
        stock_pnl = {}
        
        for sell_tx in sell_transactions:
            stock_code = sell_tx.stock_code
            
            if stock_code not in stock_pnl:
                stock_pnl[stock_code] = {
                    'total_sell_amount': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'stock_name': self.stock_service.get_stock_name(stock_code)
                }
            
            # 賣出金額（實收）
            sell_amount = sell_tx.total_amount  # 已扣除手續費與稅
            stock_pnl[stock_code]['total_sell_amount'] += sell_amount
            
            # 計算對應的成本（使用當時的平均成本）
            # 簡化版本：假設每次賣出都使用當時的平均成本
            cost = sell_tx.price_per_share * sell_tx.quantity
            stock_pnl[stock_code]['total_cost'] += cost
        
        # 轉換為 RealizedPnL 格式
        result = []
        for stock_code, data in stock_pnl.items():
            realized_pnl = data['total_sell_amount'] - data['total_cost']
            realized_pnl_pct = (realized_pnl / data['total_cost'] * 100) if data['total_cost'] > 0 else Decimal('0')
            
            result.append(RealizedPnL(
                stock_code=stock_code,
                stock_name=data['stock_name'],
                total_buy_amount=data['total_cost'],
                total_sell_amount=data['total_sell_amount'],
                realized_pnl=realized_pnl,
                realized_pnl_pct=realized_pnl_pct.quantize(Decimal('0.01'))
            ))
        
        return result
    
    def _get_investor(self, line_user_id: str, investor_name: str) -> Optional[Investor]:
        """取得投資人"""
        line_user = self.db.query(LineUser).filter(
            LineUser.line_user_id == line_user_id
        ).first()
        
        if not line_user:
            return None
        
        investor = self.db.query(Investor).filter(
            and_(
                Investor.line_user_id == line_user.id,
                Investor.investor_name == investor_name
            )
        ).first()
        
        return investor
    
    def get_all_investors_summary(self, line_user_id: str) -> List[dict]:
        """
        取得所有投資人的簡要資訊
        
        Args:
            line_user_id: LINE 用戶 ID
            
        Returns:
            List[dict]: 投資人簡要資訊列表
        """
        line_user = self.db.query(LineUser).filter(
            LineUser.line_user_id == line_user_id
        ).first()
        
        if not line_user:
            return []
        
        investors = self.db.query(Investor).filter(
            Investor.line_user_id == line_user.id
        ).all()
        
        result = []
        for investor in investors:
            # 計算持股數量
            holdings_count = self.db.query(func.count(Holding.stock_code)).filter(
                Holding.investor_id == investor.id
            ).scalar()
            
            # 計算總投入金額
            total_invested = self.db.query(func.sum(Holding.total_invested)).filter(
                Holding.investor_id == investor.id
            ).scalar() or Decimal('0')
            
            result.append({
                'name': investor.investor_name,
                'is_self': investor.is_self,
                'total_stocks': holdings_count,
                'total_invested': float(total_invested)
            })
        
        return result
