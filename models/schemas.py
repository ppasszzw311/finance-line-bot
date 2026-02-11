"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum


class TransactionTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


# ============================================================
# Request Schemas
# ============================================================

class TransactionCreate(BaseModel):
    """創建交易記錄的請求"""
    investor_name: str = Field(..., max_length=50, description="投資人名稱")
    stock_code: str = Field(..., max_length=10, description="股票代碼")
    transaction_type: TransactionTypeEnum = Field(..., description="交易類型")
    quantity: Decimal = Field(..., gt=0, description="股數")
    price_per_share: Decimal = Field(..., gt=0, description="每股價格")
    transaction_date: Optional[date] = Field(default=None, description="交易日期")
    notes: Optional[str] = Field(default=None, description="備註")

    class Config:
        json_schema_extra = {
            "example": {
                "investor_name": "我",
                "stock_code": "2330.TW",
                "transaction_type": "BUY",
                "quantity": 100,
                "price_per_share": 250.00,
                "transaction_date": "2026-02-11",
                "notes": "長期投資"
            }
        }


class ParsedTransaction(BaseModel):
    """解析自然語言後的交易資料"""
    investor_name: str
    stock_code: str
    stock_name: Optional[str] = None
    transaction_type: TransactionTypeEnum
    quantity: Decimal
    price_per_share: Decimal
    

# ============================================================
# Response Schemas
# ============================================================

class TransactionResponse(BaseModel):
    """交易記錄回應"""
    id: str
    investor_name: str
    stock_code: str
    transaction_type: str
    quantity: Decimal
    price_per_share: Decimal
    transaction_fee: Decimal
    transaction_tax: Decimal
    total_amount: Decimal
    transaction_date: date
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class HoldingResponse(BaseModel):
    """持股資訊回應"""
    stock_code: str
    stock_name: Optional[str] = None
    total_quantity: Decimal
    average_cost: Decimal
    total_invested: Decimal
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[Decimal] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """投資組合總覽"""
    investor_name: str
    total_stocks: int
    total_invested: Decimal
    current_value: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: Decimal
    holdings: List[HoldingResponse]


class RealizedPnL(BaseModel):
    """已實現損益"""
    stock_code: str
    stock_name: Optional[str] = None
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    realized_pnl: Decimal
    realized_pnl_pct: Decimal


class ComparisonResult(BaseModel):
    """績效比較結果"""
    investor_name: str
    total_invested: Decimal
    current_value: Decimal
    total_return: Decimal
    return_pct: Decimal
    rank: Optional[int] = None


class ETFComparisonResult(BaseModel):
    """與 ETF 比較結果"""
    investor_name: str
    investor_return_pct: Decimal
    etf_code: str
    etf_name: str
    etf_return_pct: Decimal
    outperformance: Decimal  # 超額報酬


class StockInfoResponse(BaseModel):
    """股票資訊回應"""
    security_id: str
    stock_name_zh: str
    market: Optional[str] = None
    industry: Optional[str] = None

    class Config:
        from_attributes = True


class StockPriceResponse(BaseModel):
    """股價資訊回應"""
    stock_code: str
    current_price: Decimal
    previous_close: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    fetched_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# LINE Bot Message Schemas
# ============================================================

class LineWebhookEvent(BaseModel):
    """LINE Webhook 事件"""
    type: str
    timestamp: int
    source: dict
    message: Optional[dict] = None
    replyToken: Optional[str] = None
