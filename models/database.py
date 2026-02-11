"""
Database models using SQLAlchemy ORM
"""
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    create_engine, Column, String, DateTime, Boolean, 
    Date, Numeric, Text, ForeignKey, Enum, CheckConstraint,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid
import enum

# Base class for all models
Base = declarative_base()

# Enums
class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class LineUser(Base):
    """LINE 用戶主表"""
    __tablename__ = "line_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSONB, default={})
    
    # Relationships
    investors = relationship("Investor", back_populates="line_user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LineUser(id={self.id}, line_user_id={self.line_user_id}, name={self.display_name})>"


class Investor(Base):
    """投資人表（被記錄者）"""
    __tablename__ = "investors"
    __table_args__ = (
        UniqueConstraint('line_user_id', 'investor_name', name='uq_line_user_investor_name'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id = Column(UUID(as_uuid=True), ForeignKey('line_users.id', ondelete='CASCADE'), nullable=False)
    investor_name = Column(String(50), nullable=False)
    is_self = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    line_user = relationship("LineUser", back_populates="investors")
    transactions = relationship("Transaction", back_populates="investor", cascade="all, delete-orphan")
    holdings = relationship("Holding", back_populates="investor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Investor(id={self.id}, name={self.investor_name}, is_self={self.is_self})>"


class Transaction(Base):
    """交易記錄表"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_id = Column(UUID(as_uuid=True), ForeignKey('investors.id', ondelete='CASCADE'), nullable=False)
    stock_code = Column(String(10), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Numeric(12, 4), nullable=False)
    price_per_share = Column(Numeric(10, 2), nullable=False)
    transaction_fee = Column(Numeric(10, 2), default=0)
    transaction_tax = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    transaction_date = Column(Date, default=date.today)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('price_per_share > 0', name='check_price_positive'),
        Index('idx_investor_date', 'investor_id', 'transaction_date'),
    )
    
    # Relationships
    investor = relationship("Investor", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, {self.transaction_type.value} {self.stock_code} {self.quantity}@{self.price_per_share})>"


class Holding(Base):
    """當前持股表"""
    __tablename__ = "holdings"
    
    investor_id = Column(UUID(as_uuid=True), ForeignKey('investors.id', ondelete='CASCADE'), primary_key=True)
    stock_code = Column(String(10), primary_key=True)
    total_quantity = Column(Numeric(12, 4), nullable=False)
    average_cost = Column(Numeric(10, 2), nullable=False)
    total_invested = Column(Numeric(15, 2), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('total_quantity >= 0', name='check_holding_quantity_non_negative'),
    )
    
    # Relationships
    investor = relationship("Investor", back_populates="holdings")
    
    def __repr__(self):
        return f"<Holding(investor_id={self.investor_id}, {self.stock_code}: {self.total_quantity}@{self.average_cost})>"


class DimSecurity(Base):
    """股票資訊表（使用現有的 dim_security，由外部服務每日更新）"""
    __tablename__ = "dim_security"
    
    security_id = Column(String(20), primary_key=True)
    name_zh = Column(String(100), nullable=False, index=True)
    market = Column(String(20))  # TWSE, TPEx 等
    industry = Column(String(100))
    isin = Column(String(20))
    listing_date = Column(DateTime)
    status = Column(String(20))
    day_trading_flag = Column(String(10))
    odd_lot_enabled = Column(String(10))
    updated_at = Column(DateTime)
    
    def __repr__(self):
        return f"<DimSecurity({self.security_id}: {self.name_zh})>"


class StockPriceCache(Base):
    """股價緩存表"""
    __tablename__ = "stock_prices_cache"
    
    stock_code = Column(String(10), primary_key=True)
    current_price = Column(Numeric(10, 2))
    previous_close = Column(Numeric(10, 2))
    change_percent = Column(Numeric(6, 2))
    data_source = Column(String(20), default='yfinance')
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<StockPriceCache({self.stock_code}: ${self.current_price})>"


# Database connection setup
def get_database_url():
    """Get database URL from environment variable"""
    return os.getenv('DATABASE_URL', 'postgresql://localhost:5432/finance_bot')


def create_db_engine():
    """Create SQLAlchemy engine"""
    database_url = get_database_url()
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        echo=False  # Set to True for SQL query logging
    )
    return engine


def get_session_maker():
    """Get session maker for database operations"""
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_db():
    """Initialize database (create all tables)"""
    engine = create_db_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


# Dependency for FastAPI
def get_db():
    """Dependency for getting database session in FastAPI"""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
