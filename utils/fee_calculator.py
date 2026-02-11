"""
手續費計算工具
台灣股市交易成本計算
"""
from decimal import Decimal, ROUND_HALF_UP


# 台灣股市手續費率
BROKER_FEE_RATE = Decimal('0.001425')  # 券商手續費 0.1425%
TRANSACTION_TAX_RATE = Decimal('0.003')  # 證券交易稅 0.3% (僅賣出收取)
MIN_BROKER_FEE = Decimal('20')  # 最低手續費 20 元（部分券商有此限制）


def calculate_buy_fees(quantity: Decimal, price_per_share: Decimal) -> dict:
    """
    計算買入交易的手續費
    
    Args:
        quantity: 股數
        price_per_share: 每股價格
        
    Returns:
        dict: {
            'transaction_amount': 交易金額,
            'broker_fee': 券商手續費,
            'transaction_tax': 證交稅 (買入為0),
            'total_fee': 總手續費,
            'total_cost': 總成本（含手續費）
        }
    """
    transaction_amount = quantity * price_per_share
    
    # 計算券商手續費
    broker_fee = (transaction_amount * BROKER_FEE_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # 買入不收證交稅
    transaction_tax = Decimal('0')
    
    # 總手續費
    total_fee = broker_fee + transaction_tax
    
    # 總成本
    total_cost = transaction_amount + total_fee
    
    return {
        'transaction_amount': transaction_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'broker_fee': broker_fee,
        'transaction_tax': transaction_tax,
        'total_fee': total_fee,
        'total_cost': total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    }


def calculate_sell_fees(quantity: Decimal, price_per_share: Decimal) -> dict:
    """
    計算賣出交易的手續費
    
    Args:
        quantity: 股數
        price_per_share: 每股價格
        
    Returns:
        dict: {
            'transaction_amount': 交易金額,
            'broker_fee': 券商手續費,
            'transaction_tax': 證交稅,
            'total_fee': 總手續費,
            'net_proceeds': 實收金額（扣除手續費）
        }
    """
    transaction_amount = quantity * price_per_share
    
    # 計算券商手續費
    broker_fee = (transaction_amount * BROKER_FEE_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # 計算證交稅
    transaction_tax = (transaction_amount * TRANSACTION_TAX_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # 總手續費
    total_fee = broker_fee + transaction_tax
    
    # 實收金額
    net_proceeds = transaction_amount - total_fee
    
    return {
        'transaction_amount': transaction_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'broker_fee': broker_fee,
        'transaction_tax': transaction_tax,
        'total_fee': total_fee,
        'net_proceeds': net_proceeds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    }


def calculate_transaction_fees(transaction_type: str, quantity: Decimal, price_per_share: Decimal) -> dict:
    """
    根據交易類型計算手續費
    
    Args:
        transaction_type: 'BUY' 或 'SELL'
        quantity: 股數
        price_per_share: 每股價格
        
    Returns:
        dict: 手續費明細
    """
    if transaction_type.upper() == 'BUY':
        return calculate_buy_fees(quantity, price_per_share)
    elif transaction_type.upper() == 'SELL':
        return calculate_sell_fees(quantity, price_per_share)
    else:
        raise ValueError(f"Invalid transaction type: {transaction_type}. Must be 'BUY' or 'SELL'")


def format_currency(amount: Decimal) -> str:
    """格式化金額為台幣格式"""
    return f"${amount:,.2f}"


def calculate_break_even_price(buy_price: Decimal) -> Decimal:
    """
    計算損益兩平價格（考慮買賣手續費）
    
    Args:
        buy_price: 買入價格
        
    Returns:
        Decimal: 損益兩平價格
    """
    # 買入成本率 = 1 + 0.001425
    buy_cost_rate = Decimal('1') + BROKER_FEE_RATE
    
    # 賣出成本率 = 1 - 0.001425 - 0.003
    sell_cost_rate = Decimal('1') - BROKER_FEE_RATE - TRANSACTION_TAX_RATE
    
    # 損益兩平價 = 買入價 * (買入成本率 / 賣出成本率)
    break_even_price = (buy_price * buy_cost_rate / sell_cost_rate).quantize(
        Decimal('0.01'), 
        rounding=ROUND_HALF_UP
    )
    
    return break_even_price


if __name__ == "__main__":
    # 測試範例
    print("=== 買入 100 股 @ $250 ===")
    buy_result = calculate_buy_fees(Decimal('100'), Decimal('250'))
    for key, value in buy_result.items():
        print(f"{key}: {format_currency(value) if isinstance(value, Decimal) else value}")
    
    print("\n=== 賣出 100 股 @ $280 ===")
    sell_result = calculate_sell_fees(Decimal('100'), Decimal('280'))
    for key, value in sell_result.items():
        print(f"{key}: {format_currency(value) if isinstance(value, Decimal) else value}")
    
    print("\n=== 損益兩平價格（買入價 $250）===")
    break_even = calculate_break_even_price(Decimal('250'))
    print(f"損益兩平價: {format_currency(break_even)}")
