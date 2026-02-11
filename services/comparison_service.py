"""
績效比較服務：投資人之間比較、與 ETF 比較
"""
from decimal import Decimal
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from models.schemas import ComparisonResult, ETFComparisonResult
from services.portfolio_service import PortfolioService
from services.stock_service import StockService
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


class ComparisonService:
    """績效比較服務"""
    
    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.stock_service = StockService(db)
    
    def compare_investors(
        self,
        line_user_id: str,
        investor_names: List[str]
    ) -> List[ComparisonResult]:
        """
        比較多個投資人的績效
        
        Args:
            line_user_id: LINE 用戶 ID
            investor_names: 投資人名稱列表
            
        Returns:
            List[ComparisonResult]: 績效比較結果（按報酬率降序排列）
        """
        results = []
        
        for name in investor_names:
            portfolio = self.portfolio_service.get_portfolio(line_user_id, name)
            
            if portfolio and portfolio.total_invested > 0:
                total_return = portfolio.total_unrealized_pnl
                return_pct = portfolio.total_unrealized_pnl_pct
                
                results.append(ComparisonResult(
                    investor_name=name,
                    total_invested=portfolio.total_invested,
                    current_value=portfolio.current_value,
                    total_return=total_return,
                    return_pct=return_pct
                ))
        
        # 按報酬率排序
        results.sort(key=lambda x: x.return_pct, reverse=True)
        
        # 添加排名
        for rank, result in enumerate(results, start=1):
            result.rank = rank
        
        return results
    
    def compare_with_etf(
        self,
        line_user_id: str,
        investor_name: str,
        etf_code: str,
        start_date: Optional[date] = None
    ) -> Optional[ETFComparisonResult]:
        """
        將投資人績效與 ETF 比較
        
        Args:
            line_user_id: LINE 用戶 ID
            investor_name: 投資人名稱
            etf_code: ETF 代碼（如 0050.TW）
            start_date: 比較起始日期（預設為 1 年前）
            
        Returns:
            Optional[ETFComparisonResult]: 比較結果
        """
        # 取得投資人績效
        portfolio = self.portfolio_service.get_portfolio(line_user_id, investor_name)
        
        if not portfolio or portfolio.total_invested == 0:
            return None
        
        investor_return_pct = portfolio.total_unrealized_pnl_pct
        
        # 計算 ETF 期間報酬率
        etf_return_pct = self._calculate_etf_return(etf_code, start_date)
        
        if etf_return_pct is None:
            logger.warning(f"Failed to fetch ETF return for {etf_code}")
            etf_return_pct = Decimal('0')
        
        # 計算超額報酬
        outperformance = investor_return_pct - etf_return_pct
        
        # 取得 ETF 名稱
        etf_name = self.stock_service.get_stock_name(etf_code)
        
        return ETFComparisonResult(
            investor_name=investor_name,
            investor_return_pct=investor_return_pct,
            etf_code=etf_code,
            etf_name=etf_name,
            etf_return_pct=etf_return_pct,
            outperformance=outperformance
        )
    
    def _calculate_etf_return(
        self,
        etf_code: str,
        start_date: Optional[date] = None
    ) -> Optional[Decimal]:
        """
        計算 ETF 期間報酬率
        
        Args:
            etf_code: ETF 代碼
            start_date: 起始日期（預設為 1 年前）
            
        Returns:
            Optional[Decimal]: 報酬率（百分比）
        """
        try:
            if start_date is None:
                # 預設比較 1 年期報酬
                start_date = date.today() - timedelta(days=365)
            
            # 使用 yfinance 取得歷史資料
            ticker = yf.Ticker(etf_code)
            history = ticker.history(start=start_date, end=date.today())
            
            if history.empty or len(history) < 2:
                logger.warning(f"Insufficient data for {etf_code}")
                return None
            
            # 計算報酬率
            start_price = float(history['Close'].iloc[0])
            end_price = float(history['Close'].iloc[-1])
            
            return_pct = ((end_price - start_price) / start_price * 100)
            
            return Decimal(str(return_pct)).quantize(Decimal('0.01'))
        
        except Exception as e:
            logger.error(f"Error calculating ETF return for {etf_code}: {e}")
            return None
    
    def get_leaderboard(
        self,
        line_user_id: str,
        include_etfs: bool = True
    ) -> List[dict]:
        """
        取得排行榜（投資人 + ETF）
        
        Args:
            line_user_id: LINE 用戶 ID
            include_etfs: 是否包含 ETF 基準
            
        Returns:
            List[dict]: 排行榜資料
        """
        leaderboard = []
        
        # 取得所有投資人
        investors_summary = self.portfolio_service.get_all_investors_summary(line_user_id)
        
        for inv in investors_summary:
            portfolio = self.portfolio_service.get_portfolio(line_user_id, inv['name'])
            if portfolio and portfolio.total_invested > 0:
                leaderboard.append({
                    'name': inv['name'],
                    'type': 'investor',
                    'return_pct': float(portfolio.total_unrealized_pnl_pct),
                    'total_invested': float(portfolio.total_invested),
                    'current_value': float(portfolio.current_value)
                })
        
        # 添加 ETF 基準（寫死 0050, 0056, 00878）
        if include_etfs:
            benchmark_etfs = self.stock_service.get_benchmark_etfs()
            for etf_code in benchmark_etfs:
                etf_return = self._calculate_etf_return(etf_code)
                if etf_return:
                    etf_name = self.stock_service.get_stock_name(etf_code)
                    leaderboard.append({
                        'name': etf_name,
                        'type': 'etf',
                        'return_pct': float(etf_return),
                        'total_invested': None,
                        'current_value': None
                    })
        
        # 排序
        leaderboard.sort(key=lambda x: x['return_pct'], reverse=True)
        
        # 添加排名
        for rank, item in enumerate(leaderboard, start=1):
            item['rank'] = rank
        
        return leaderboard
