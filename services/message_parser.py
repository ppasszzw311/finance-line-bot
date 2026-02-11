"""
自然語言訊息解析器
解析用戶輸入的交易訊息，提取股票、數量、價格等資訊
"""
import re
from typing import Optional
from decimal import Decimal
from models.schemas import ParsedTransaction, TransactionTypeEnum
from services.stock_service import StockService
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class MessageParser:
    """訊息解析器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stock_service = StockService(db)
    
    def parse_transaction_message(self, message: str) -> Optional[ParsedTransaction]:
        """
        解析交易訊息
        
        支援格式：
        - "買 2330 100股 250元"
        - "我買台積電 50股 @600"
        - "小明賣鴻海200股 價格120"
        - "賣出 0050 10股 150.5元"
        
        Args:
            message: 用戶輸入的訊息
            
        Returns:
            Optional[ParsedTransaction]: 解析結果或 None
        """
        try:
            # 1. 判斷交易類型
            transaction_type = self._extract_transaction_type(message)
            if not transaction_type:
                return None
            
            # 2. 提取投資人名稱
            investor_name = self._extract_investor_name(message)
            
            # 3. 提取股票資訊
            stock_code, stock_name = self._extract_stock_info(message)
            if not stock_code:
                return None
            
            # 4. 提取數量
            quantity = self._extract_quantity(message)
            if not quantity:
                return None
            
            # 5. 提取價格
            price = self._extract_price(message)
            if not price:
                return None
            
            return ParsedTransaction(
                investor_name=investor_name,
                stock_code=stock_code,
                stock_name=stock_name,
                transaction_type=transaction_type,
                quantity=quantity,
                price_per_share=price
            )
        
        except Exception as e:
            logger.error(f"Error parsing message '{message}': {e}")
            return None
    
    def _extract_transaction_type(self, message: str) -> Optional[TransactionTypeEnum]:
        """提取交易類型"""
        if re.search(r'買入|買進|買', message):
            return TransactionTypeEnum.BUY
        elif re.search(r'賣出|賣掉|賣', message):
            return TransactionTypeEnum.SELL
        return None
    
    def _extract_investor_name(self, message: str) -> str:
        """
        提取投資人名稱
        
        規則：
        - 若訊息開頭有「XXX買」或「XXX賣」，則提取 XXX
        - 若有「我」，則為「我」
        - 否則預設為「我」
        """
        # 檢查是否有明確的人名（在買賣動作前）
        # 例如：「小明買」、「老王賣出」
        name_pattern = r'^([\u4e00-\u9fa5]{2,4})(?:買|賣)'
        match = re.search(name_pattern, message)
        if match:
            name = match.group(1)
            # 排除「我買」的情況
            if name == '我':
                return '我'
            return name
        
        # 檢查是否有「我」
        if '我' in message:
            return '我'
        
        # 預設為「我」
        return '我'
    
    def _extract_stock_info(self, message: str) -> tuple[Optional[str], Optional[str]]:
        """
        提取股票資訊（代碼或名稱）
        
        Returns:
            tuple: (stock_code, stock_name)
        """
        # 嘗試提取 4 位數字代碼
        code_pattern = r'(\d{4})'
        code_match = re.search(code_pattern, message)
        
        if code_match:
            code = code_match.group(1)
            stock_code = self.stock_service.convert_name_to_code(code)
            if stock_code:
                stock_name = self.stock_service.get_stock_name(stock_code)
                return stock_code, stock_name
        
        # 嘗試提取中文股票名稱
        # 常見模式：在買賣動作後、數量前
        name_pattern = r'(?:買|賣|買入|賣出)\s*([\u4e00-\u9fa5]{2,6})'
        name_match = re.search(name_pattern, message)
        
        if name_match:
            name = name_match.group(1)
            # 排除人名（如果人名剛好被匹配到）
            if name not in ['我', '你', '他', '她']:
                stock_code = self.stock_service.convert_name_to_code(name)
                if stock_code:
                    return stock_code, name
        
        return None, None
    
    def _extract_quantity(self, message: str) -> Optional[Decimal]:
        """
        提取股數
        
        支援格式：
        - "100股"
        - "50 股"
        - "1000張" (1張 = 1000股)
        """
        # 提取「X股」格式
        stock_pattern = r'(\d+(?:\.\d+)?)\s*股'
        match = re.search(stock_pattern, message)
        if match:
            return Decimal(match.group(1))
        
        # 提取「X張」格式（1張 = 1000股）
        lot_pattern = r'(\d+(?:\.\d+)?)\s*張'
        match = re.search(lot_pattern, message)
        if match:
            lots = Decimal(match.group(1))
            return lots * 1000
        
        return None
    
    def _extract_price(self, message: str) -> Optional[Decimal]:
        """
        提取價格
        
        支援格式：
        - "250元"
        - "@600"
        - "@ $150.5"
        - "價格120"
        """
        # 提取「X元」格式
        yuan_pattern = r'(\d+(?:\.\d+)?)\s*元'
        match = re.search(yuan_pattern, message)
        if match:
            return Decimal(match.group(1))
        
        # 提取「@X」或「@ $X」格式
        at_pattern = r'@\s*\$?\s*(\d+(?:\.\d+)?)'
        match = re.search(at_pattern, message)
        if match:
            return Decimal(match.group(1))
        
        # 提取「價格X」格式
        price_pattern = r'價格\s*(\d+(?:\.\d+)?)'
        match = re.search(price_pattern, message)
        if match:
            return Decimal(match.group(1))
        
        return None
    
    def validate_transaction(self, parsed: ParsedTransaction) -> tuple[bool, str]:
        """
        驗證解析結果是否完整
        
        Returns:
            tuple: (是否有效, 錯誤訊息)
        """
        if not parsed.stock_code:
            return False, "無法識別股票代碼，請確認股票名稱或代碼是否正確"
        
        if parsed.quantity <= 0:
            return False, "股數必須大於 0"
        
        if parsed.price_per_share <= 0:
            return False, "價格必須大於 0"
        
        return True, ""
    
    def generate_confirmation_message(self, parsed: ParsedTransaction) -> str:
        """
        生成確認訊息
        
        Args:
            parsed: 解析結果
            
        Returns:
            str: 確認訊息文字
        """
        action = "買入" if parsed.transaction_type == TransactionTypeEnum.BUY else "賣出"
        stock_display = f"{parsed.stock_name}({parsed.stock_code.replace('.TW', '')})" if parsed.stock_name else parsed.stock_code
        
        # 計算總金額（簡易估算，不含手續費）
        total = float(parsed.quantity * parsed.price_per_share)
        
        message = f"""✅ 請確認交易資訊

👤 投資人: {parsed.investor_name}
🔵 動作: {action}
📊 股票: {stock_display}
📈 數量: {parsed.quantity} 股
💰 價格: ${parsed.price_per_share}
💵 總金額: ${total:,.2f}

請回覆「確認」以記錄此交易"""
        
        return message


# 單例測試
if __name__ == "__main__":
    test_messages = [
        "買 2330 100股 250元",
        "我買台積電 50股 @600",
        "小明賣鴻海200股 價格120",
        "賣出 0050 10股 150.5元"
    ]
    
    # 需要資料庫連線才能完整測試
    print("Message Parser Test Cases:")
    for msg in test_messages:
        print(f"\n輸入: {msg}")
        # parser = MessageParser(db_session)
        # result = parser.parse_transaction_message(msg)
        # print(f"結果: {result}")
