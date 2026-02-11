"""
交易服務：處理交易記錄與持股更新
"""
from decimal import Decimal
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database import LineUser, Investor, Transaction, Holding, TransactionType
from models.schemas import TransactionCreate, TransactionResponse, ParsedTransaction
from utils.fee_calculator import calculate_transaction_fees
import logging
import uuid

logger = logging.getLogger(__name__)


class TransactionService:
    """交易服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_line_user(self, line_user_id: str, display_name: str = None) -> LineUser:
        """取得或建立 LINE 用戶"""
        user = self.db.query(LineUser).filter(
            LineUser.line_user_id == line_user_id
        ).first()
        
        if not user:
            user = LineUser(
                line_user_id=line_user_id,
                display_name=display_name or line_user_id
            )
            self.db.add(user)
            
            # 同時建立預設投資人（我）
            default_investor = Investor(
                line_user_id=user.id,
                investor_name="我",
                is_self=True
            )
            self.db.add(default_investor)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Created new LINE user: {line_user_id}")
        
        return user
    
    def get_or_create_investor(self, line_user: LineUser, investor_name: str) -> Investor:
        """取得或建立投資人"""
        investor = self.db.query(Investor).filter(
            and_(
                Investor.line_user_id == line_user.id,
                Investor.investor_name == investor_name
            )
        ).first()
        
        if not investor:
            is_self = (investor_name == "我")
            investor = Investor(
                line_user_id=line_user.id,
                investor_name=investor_name,
                is_self=is_self
            )
            self.db.add(investor)
            self.db.commit()
            self.db.refresh(investor)
            logger.info(f"Created new investor: {investor_name} for user {line_user.line_user_id}")
        
        return investor
    
    def create_transaction(
        self,
        line_user_id: str,
        transaction_data: ParsedTransaction,
        transaction_date: date = None
    ) -> TransactionResponse:
        """
        建立交易記錄並更新持股
        
        Args:
            line_user_id: LINE 用戶 ID
            transaction_data: 交易資料
            transaction_date: 交易日期（預設為今天）
            
        Returns:
            TransactionResponse: 交易記錄
        """
        try:
            # 1. 取得或建立用戶與投資人
            line_user = self.get_or_create_line_user(line_user_id)
            investor = self.get_or_create_investor(line_user, transaction_data.investor_name)
            
            # 2. 計算手續費
            fees = calculate_transaction_fees(
                transaction_data.transaction_type.value,
                transaction_data.quantity,
                transaction_data.price_per_share
            )
            
            # 3. 建立交易記錄
            transaction = Transaction(
                investor_id=investor.id,
                stock_code=transaction_data.stock_code,
                transaction_type=TransactionType[transaction_data.transaction_type.value],
                quantity=transaction_data.quantity,
                price_per_share=transaction_data.price_per_share,
                transaction_fee=fees['broker_fee'],
                transaction_tax=fees.get('transaction_tax', Decimal('0')),
                total_amount=fees['total_cost'] if transaction_data.transaction_type == TransactionTypeEnum.BUY else fees['net_proceeds'],
                transaction_date=transaction_date or date.today()
            )
            
            self.db.add(transaction)
            self.db.flush()  # 取得 transaction.id
            
            # 4. 更新持股
            self._update_holdings(investor.id, transaction)
            
            self.db.commit()
            self.db.refresh(transaction)
            
            logger.info(f"Transaction created: {transaction.id}")
            
            return TransactionResponse(
                id=str(transaction.id),
                investor_name=investor.investor_name,
                stock_code=transaction.stock_code,
                transaction_type=transaction.transaction_type.value,
                quantity=transaction.quantity,
                price_per_share=transaction.price_per_share,
                transaction_fee=transaction.transaction_fee,
                transaction_tax=transaction.transaction_tax,
                total_amount=transaction.total_amount,
                transaction_date=transaction.transaction_date,
                notes=transaction.notes,
                created_at=transaction.created_at
            )
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating transaction: {e}")
            raise
    
    def _update_holdings(self, investor_id: uuid.UUID, transaction: Transaction):
        """
        更新持股（平均成本法）
        
        Args:
            investor_id: 投資人 ID
            transaction: 交易記錄
        """
        holding = self.db.query(Holding).filter(
            and_(
                Holding.investor_id == investor_id,
                Holding.stock_code == transaction.stock_code
            )
        ).first()
        
        if transaction.transaction_type == TransactionType.BUY:
            if holding:
                # 更新現有持股（平均成本法）
                new_quantity = holding.total_quantity + transaction.quantity
                new_total_invested = holding.total_invested + transaction.total_amount
                new_average_cost = new_total_invested / new_quantity
                
                holding.total_quantity = new_quantity
                holding.average_cost = new_average_cost
                holding.total_invested = new_total_invested
            else:
                # 新增持股
                holding = Holding(
                    investor_id=investor_id,
                    stock_code=transaction.stock_code,
                    total_quantity=transaction.quantity,
                    average_cost=transaction.price_per_share,
                    total_invested=transaction.total_amount
                )
                self.db.add(holding)
        
        elif transaction.transaction_type == TransactionType.SELL:
            if not holding:
                raise ValueError(f"Cannot sell {transaction.stock_code}: No holdings found")
            
            if holding.total_quantity < transaction.quantity:
                raise ValueError(
                    f"Cannot sell {transaction.quantity} shares of {transaction.stock_code}: "
                    f"Only {holding.total_quantity} shares available"
                )
            
            # 減少持股
            new_quantity = holding.total_quantity - transaction.quantity
            
            if new_quantity == 0:
                # 完全賣出，刪除持股記錄
                self.db.delete(holding)
            else:
                # 部分賣出，更新數量（平均成本維持不變）
                # 按比例減少總投入金額
                remaining_ratio = new_quantity / holding.total_quantity
                holding.total_quantity = new_quantity
                holding.total_invested = holding.total_invested * remaining_ratio
    
    def get_transactions(
        self,
        line_user_id: str,
        investor_name: Optional[str] = None,
        stock_code: Optional[str] = None,
        limit: int = 50
    ) -> List[TransactionResponse]:
        """
        查詢交易記錄
        
        Args:
            line_user_id: LINE 用戶 ID
            investor_name: 投資人名稱（可選）
            stock_code: 股票代碼（可選）
            limit: 返回筆數限制
            
        Returns:
            List[TransactionResponse]: 交易記錄列表
        """
        line_user = self.db.query(LineUser).filter(
            LineUser.line_user_id == line_user_id
        ).first()
        
        if not line_user:
            return []
        
        query = self.db.query(Transaction).join(Investor).filter(
            Investor.line_user_id == line_user.id
        )
        
        if investor_name:
            query = query.filter(Investor.investor_name == investor_name)
        
        if stock_code:
            query = query.filter(Transaction.stock_code == stock_code)
        
        transactions = query.order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for t in transactions:
            result.append(TransactionResponse(
                id=str(t.id),
                investor_name=t.investor.investor_name,
                stock_code=t.stock_code,
                transaction_type=t.transaction_type.value,
                quantity=t.quantity,
                price_per_share=t.price_per_share,
                transaction_fee=t.transaction_fee,
                transaction_tax=t.transaction_tax,
                total_amount=t.total_amount,
                transaction_date=t.transaction_date,
                notes=t.notes,
                created_at=t.created_at
            ))
        
        return result
    
    def get_investors(self, line_user_id: str) -> List[dict]:
        """
        取得用戶記錄的所有投資人
        
        Args:
            line_user_id: LINE 用戶 ID
            
        Returns:
            List[dict]: 投資人列表
        """
        line_user = self.db.query(LineUser).filter(
            LineUser.line_user_id == line_user_id
        ).first()
        
        if not line_user:
            return []
        
        investors = self.db.query(Investor).filter(
            Investor.line_user_id == line_user.id
        ).all()
        
        return [
            {
                "id": str(inv.id),
                "name": inv.investor_name,
                "is_self": inv.is_self
            }
            for inv in investors
        ]


# 修正 import
from models.schemas import TransactionTypeEnum
