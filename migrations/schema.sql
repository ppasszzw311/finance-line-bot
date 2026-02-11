-- LINE Bot Finance Tracker Database Schema
-- 部署到 Zeabur PostgreSQL 時執行此檔案

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 交易類型 Enum
CREATE TYPE transaction_type AS ENUM ('BUY', 'SELL');

-- 股票類型 Enum
CREATE TYPE stock_type AS ENUM ('STOCK', 'ETF');

-- ============================================================
-- LINE 用戶主表
-- ============================================================
CREATE TABLE line_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    line_user_id VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_line_users_line_user_id ON line_users(line_user_id);

-- ============================================================
-- 投資人表（被記錄者）
-- ============================================================
CREATE TABLE investors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    line_user_id UUID NOT NULL REFERENCES line_users(id) ON DELETE CASCADE,
    investor_name VARCHAR(50) NOT NULL,
    is_self BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(line_user_id, investor_name)
);

CREATE INDEX idx_investors_line_user_id ON investors(line_user_id);

-- ============================================================
-- 交易記錄表
-- ============================================================
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    transaction_type transaction_type NOT NULL,
    quantity DECIMAL(12, 4) NOT NULL CHECK (quantity > 0),
    price_per_share DECIMAL(10, 2) NOT NULL CHECK (price_per_share > 0),
    transaction_fee DECIMAL(10, 2) DEFAULT 0,
    transaction_tax DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL,
    transaction_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_investor_id ON transactions(investor_id, transaction_date DESC);
CREATE INDEX idx_transactions_stock_code ON transactions(stock_code);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);

-- ============================================================
-- 當前持股表
-- ============================================================
CREATE TABLE holdings (
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    total_quantity DECIMAL(12, 4) NOT NULL CHECK (total_quantity >= 0),
    average_cost DECIMAL(10, 2) NOT NULL,
    total_invested DECIMAL(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(investor_id, stock_code)
);

CREATE INDEX idx_holdings_investor_id ON holdings(investor_id);

-- ============================================================
-- 股票資訊表 (使用現有的 dim_security 表)
-- ============================================================
-- 注意：dim_security 表已存在且每日自動更新
-- 欄位：security_id, name_zh, market, industry, isin, 
--       listing_date, status, day_trading_flag, odd_lot_enabled, updated_at
-- 不需要額外建立，請確保該表已存在於資料庫中

-- 為 dim_security 建立搜尋索引（如果尚未建立）
CREATE INDEX IF NOT EXISTS idx_dim_security_name ON dim_security(name_zh);
CREATE INDEX IF NOT EXISTS idx_dim_security_id ON dim_security(security_id);

-- ============================================================
-- 股價緩存表
-- ============================================================
CREATE TABLE stock_prices_cache (
    stock_code VARCHAR(10) PRIMARY KEY,
    current_price DECIMAL(10, 2),
    previous_close DECIMAL(10, 2),
    change_percent DECIMAL(6, 2),
    data_source VARCHAR(20) DEFAULT 'yfinance',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 觸發器：自動更新 last_updated 時間戳
-- ============================================================
CREATE OR REPLACE FUNCTION update_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_holdings_timestamp
    BEFORE UPDATE ON holdings
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated();

-- stock_info 已改用 dim_security，該表由外部服務維護
-- 因此不需要 update timestamp trigger

-- ============================================================
-- 視圖：投資人總覽
-- ============================================================
CREATE VIEW investor_summary AS
SELECT 
    i.id,
    i.line_user_id,
    i.investor_name,
    i.is_self,
    COUNT(DISTINCT h.stock_code) as total_stocks,
    SUM(h.total_invested) as total_invested,
    COUNT(t.id) as total_transactions
FROM investors i
LEFT JOIN holdings h ON i.id = h.investor_id
LEFT JOIN transactions t ON i.id = t.investor_id
GROUP BY i.id, i.line_user_id, i.investor_name, i.is_self;

-- ============================================================
-- 註解
-- ============================================================
COMMENT ON TABLE line_users IS 'LINE 用戶主表，記錄使用此 Bot 的 LINE 用戶';
COMMENT ON TABLE investors IS '投資人表，每個 LINE 用戶可記錄多個投資人（自己或朋友）';
COMMENT ON TABLE transactions IS '交易記錄表，記錄所有買賣交易';
COMMENT ON TABLE holdings IS '當前持股表，計算每個投資人的持股與平均成本';
COMMENT ON TABLE dim_security IS '股票資訊表（外部維護），包含完整的台股上市櫃公司資訊';
COMMENT ON TABLE stock_prices_cache IS '股價緩存表，避免頻繁呼叫外部 API';
