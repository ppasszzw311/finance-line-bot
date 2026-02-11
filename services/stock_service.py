"""
股票服務：股價查詢、股票名稱轉換、緩存管理
"""
import yfinance as yf
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from models.database import DimSecurity, StockPriceCache
from models.schemas import StockInfoResponse, StockPriceResponse
import logging

logger = logging.getLogger(__name__)

# 股價緩存有效期（分鐘）
CACHE_VALID_MINUTES = 30

# 比對大盤用的 ETF 代碼（寫死）
BENCHMARK_ETFS = ['0050', '0056', '00878']


class StockService:
    """股票相關服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_stock_by_name(self, keyword: str) -> List[StockInfoResponse]:
        """
        根據股票名稱搜尋
        
        Args:
            keyword: 搜尋關鍵字（中文股票名稱）
            
        Returns:
            List[StockInfoResponse]: 匹配的股票列表
        """
        stocks = self.db.query(DimSecurity).filter(
            DimSecurity.name_zh.like(f'%{keyword}%')
        ).limit(10).all()
        
        return [
            StockInfoResponse(
                security_id=s.security_id,
                stock_name_zh=s.name_zh,
                market=s.market,
                industry=s.industry
            )
            for s in stocks
        ]
    
    def get_stock_by_code(self, stock_code: str) -> Optional[StockInfoResponse]:
        """
        根據股票代碼查詢資訊
        
        Args:
            stock_code: 股票代碼（純數字如 2330 或帶 .TW 如 2330.TW）
            
        Returns:
            Optional[StockInfoResponse]: 股票資訊或 None
        """
        # 移除 .TW 後綴以匹配 security_id
        security_id = stock_code.replace('.TW', '')
        
        stock = self.db.query(DimSecurity).filter(
            DimSecurity.security_id == security_id
        ).first()
        
        if stock:
            return StockInfoResponse(
                security_id=stock.security_id,
                stock_name_zh=stock.name_zh,
                market=stock.market,
                industry=stock.industry
            )
        return None
    
    def convert_name_to_code(self, name_or_code: str) -> Optional[str]:
        """
        將股票名稱或代碼轉換為標準代碼格式
        
        Args:
            name_or_code: 股票名稱或代碼
            
        Returns:
            Optional[str]: 標準化的股票代碼（如 2330.TW）或 None
        """
        # 如果已經是標準格式（包含 .TW），直接返回
        if '.TW' in name_or_code:
            return name_or_code
        
        # 如果是純數字，先確認是否存在於 dim_security
        if name_or_code.isdigit():
            stock = self.db.query(DimSecurity).filter(
                DimSecurity.security_id == name_or_code
            ).first()
            
            if stock:
                # 返回帶 .TW 後綴的標準格式
                return f"{name_or_code}.TW"
            else:
                # 即使不在資料庫中也返回標準格式，讓 yfinance 嘗試
                return f"{name_or_code}.TW"
        
        # 視為中文名稱，查詢資料庫
        stocks = self.search_stock_by_name(name_or_code)
        if stocks:
            # 返回第一個匹配結果的標準格式
            return f"{stocks[0].security_id}.TW"
        
        return None
    
    def get_stock_price(self, stock_code: str, force_refresh: bool = False) -> Optional[StockPriceResponse]:
        """
        查詢股票即時價格（帶緩存）
        
        Args:
            stock_code: 股票代碼
            force_refresh: 是否強制刷新（忽略緩存）
            
        Returns:
            Optional[StockPriceResponse]: 股價資訊或 None
        """
        # 檢查緩存
        if not force_refresh:
            cached = self._get_cached_price(stock_code)
            if cached:
                return cached
        
        # 從 yfinance 抓取
        try:
            price_data = self._fetch_from_yfinance(stock_code)
            if price_data:
                # 更新緩存
                self._update_cache(stock_code, price_data)
                return price_data
        except Exception as e:
            logger.error(f"Error fetching stock price for {stock_code}: {e}")
        
        return None
    
    def _get_cached_price(self, stock_code: str) -> Optional[StockPriceResponse]:
        """檢查並返回緩存的股價"""
        cache = self.db.query(StockPriceCache).filter(
            StockPriceCache.stock_code == stock_code
        ).first()
        
        if cache:
            # 檢查緩存是否過期
            time_diff = datetime.utcnow() - cache.fetched_at
            if time_diff.total_seconds() < CACHE_VALID_MINUTES * 60:
                return StockPriceResponse(
                    stock_code=cache.stock_code,
                    current_price=cache.current_price,
                    previous_close=cache.previous_close,
                    change_percent=cache.change_percent,
                    fetched_at=cache.fetched_at
                )
        
        return None
    
    def _fetch_from_yfinance(self, stock_code: str) -> Optional[StockPriceResponse]:
        """從 yfinance 抓取股價"""
        try:
            ticker = yf.Ticker(stock_code)
            info = ticker.info
            
            # 嘗試不同的價格欄位
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose')
            
            if current_price is None:
                # 嘗試從歷史資料取得最新價格
                hist = ticker.history(period='1d')
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
            
            if current_price:
                # 計算漲跌幅
                change_percent = None
                if previous_close:
                    change_percent = ((current_price - previous_close) / previous_close * 100)
                
                return StockPriceResponse(
                    stock_code=stock_code,
                    current_price=Decimal(str(current_price)),
                    previous_close=Decimal(str(previous_close)) if previous_close else None,
                    change_percent=Decimal(str(change_percent)).quantize(Decimal('0.01')) if change_percent else None,
                    fetched_at=datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"yfinance error for {stock_code}: {e}")
        
        return None
    
    def _update_cache(self, stock_code: str, price_data: StockPriceResponse):
        """更新股價緩存"""
        try:
            cache = self.db.query(StockPriceCache).filter(
                StockPriceCache.stock_code == stock_code
            ).first()
            
            if cache:
                # 更新現有緩存
                cache.current_price = price_data.current_price
                cache.previous_close = price_data.previous_close
                cache.change_percent = price_data.change_percent
                cache.fetched_at = datetime.utcnow()
            else:
                # 新增緩存記錄
                cache = StockPriceCache(
                    stock_code=stock_code,
                    current_price=price_data.current_price,
                    previous_close=price_data.previous_close,
                    change_percent=price_data.change_percent,
                    fetched_at=datetime.utcnow()
                )
                self.db.add(cache)
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Error updating cache for {stock_code}: {e}")
        # 如果找不到，返回去除 .TW 後的代碼
        return stock_code.replace('.TW', '')
    
    def get_stock_name(self, stock_code: str) -> str:
        """取得股票中文名稱"""
        stock = self.get_stock_by_code(stock_code)
        if stock:
            return stock.stock_name_zh
        return stock_code  # 若找不到，返回代碼
    
    def batch_get_prices(self, stock_codes: List[str]) -> Dict[str, Optional[StockPriceResponse]]:
        """
        批次查詢多支股票價格
        
        Args:
            stock_codes: 股票代碼列表
            
        Returns:
            Dict[str, StockPriceResponse]: 股票代碼與價格的對照表
        """
        result = {}
        for code in stock_codes:
            result[code] = self.get_stock_price(code)
        return result
    
    def get_benchmark_etfs(self) -> List[str]:
        """
        取得大盤比對用的 ETF 列表
        
        Returns:
            List[str]: ETF 代碼列表（帶 .TW 後綴）
        """
        return [f"{code}.TW" for code in BENCHMARK_ETFS]
    
    def is_etf(self, security_id: str) -> bool:
        """
        判斷是否為 ETF（簡易規則：代碼長度 >= 5 或在基準 ETF 列表中）
        
        Args:
            security_id: 證券代碼（不含 .TW）
            
        Returns:
            bool: 是否為 ETF
        """
        # 移除可能的 .TW 後綴
        code = security_id.replace('.TW', '')
        
        # ETF 通常是 4 位數以上（如 0050, 00878）
        # 或在基準 ETF 列表中
        return code in BENCHMARK_ETFS or (code.isdigit() and len(code) >= 5)
