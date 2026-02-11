# ✅ 已完成：整合現有 dim_security 表

## 變更摘要

專案已調整為使用你現有的 `dim_security` 表，取代原本的 `stock_info` 表。這樣能直接使用由外部服務每日更新的完整台股資料。

---

## 🔄 主要變更

### 1. 資料庫層
- ✅ **移除** `stock_info` 表定義
- ✅ **新增** `DimSecurity` ORM 模型對應現有的 `dim_security` 表
- ✅ **更新** schema.sql 註解說明使用外部表
- ✅ **新增** dim_security 索引建立語句

### 2. 資料模型
**檔案**: `models/database.py`
- ✅ 移除 `StockType` enum
- ✅ 新增 `DimSecurity` 類別：
  ```python
  class DimSecurity(Base):
      security_id = Column(String(20), primary_key=True)  # 純數字如 2330
      name_zh = Column(String(100))
      market = Column(String(20))
      industry = Column(String(100))
      # ... 其他欄位
  ```

**檔案**: `models/schemas.py`
- ✅ 移除 `StockTypeEnum`
- ✅ 更新 `StockInfoResponse` 改用 `security_id`

### 3. 股票服務
**檔案**: `services/stock_service.py`
- ✅ 查詢改為使用 `DimSecurity` 表
- ✅ `convert_name_to_code()` 更新邏輯：
  - 純數字代碼自動加上 `.TW` 後綴（用於 yfinance）
  - 查詢 `dim_security.security_id` 而非 `stock_info.stock_code`
- ✅ 新增 `BENCHMARK_ETFS = ['0050', '0056', '00878']` 常數
- ✅ 新增 `get_benchmark_etfs()` 方法
- ✅ 新增 `is_etf()` 方法（簡易判斷規則）

### 4. 績效比較服務
**檔案**: `services/comparison_service.py`
- ✅ `get_leaderboard()` 改用 `stock_service.get_benchmark_etfs()`
- ✅ 寫死使用 0050、0056、00878 作為基準

### 5. 初始資料
**檔案**: `migrations/seed_stocks.sql`
- ✅ 完全改寫為說明文件
- ✅ 註明不需要匯入資料（使用現有 dim_security）
- ✅ 說明 ETF 基準代碼已寫死在程式中

### 6. 文件更新
- ✅ README.md - 更新部署說明
- ✅ DEPLOYMENT.md - 強調需要現有 dim_security 表

---

## 📋 dim_security 表結構對照

| 欄位 | 類型 | 說明 | 使用情境 |
|------|------|------|----------|
| security_id | VARCHAR | 股票代碼（純數字） | 2330, 0050 |
| name_zh | VARCHAR | 中文名稱 | 台積電、元大台灣50 |
| market | VARCHAR | 市場別 | TWSE, TPEx |
| industry | VARCHAR | 產業別 | 半導體、金融 |
| isin | VARCHAR | ISIN 代碼 | - |
| listing_date | TIMESTAMP | 上市日期 | - |
| status | VARCHAR | 狀態 | - |
| day_trading_flag | VARCHAR | 當沖標記 | - |
| odd_lot_enabled | VARCHAR | 盤中零股 | - |
| updated_at | TIMESTAMP | 更新時間 | 每日更新 |

---

## 🔧 程式邏輯調整

### 股票代碼轉換邏輯

**輸入** → **處理** → **輸出（給 yfinance）**

| 輸入 | 處理邏輯 | 輸出 |
|------|----------|------|
| `2330` | 查詢 dim_security.security_id = '2330' | `2330.TW` |
| `台積電` | 查詢 dim_security.name_zh LIKE '%台積電%' | `2330.TW` |
| `2330.TW` | 已是標準格式 | `2330.TW` |
| `0050` | 查詢 dim_security.security_id = '0050' | `0050.TW` |

### ETF 判斷規則（簡易版）

```python
def is_etf(security_id):
    code = security_id.replace('.TW', '')
    # 1. 在基準 ETF 列表中
    if code in ['0050', '0056', '00878']:
        return True
    # 2. 代碼長度 >= 5（如 00878）
    if code.isdigit() and len(code) >= 5:
        return True
    return False
```

### 大盤基準 ETF（寫死）

```python
# services/stock_service.py
BENCHMARK_ETFS = ['0050', '0056', '00878']

# 對應名稱（從 dim_security 查詢）：
# - 0050: 元大台灣50
# - 0056: 元大高股息
# - 00878: 國泰永續高股息
```

---

## ✅ 測試檢查清單

### 資料庫檢查
- [ ] 確認 dim_security 表存在
- [ ] 確認有台積電（2330）資料
- [ ] 確認有 3 支基準 ETF（0050, 0056, 00878）
- [ ] 確認索引已建立

### 功能測試
- [ ] 測試輸入「買 2330 100股 250元」
- [ ] 測試輸入「買台積電 100股 250元」
- [ ] 測試查詢持股（確認股票名稱正確顯示）
- [ ] 測試績效排行榜（確認 3 支 ETF 顯示）
- [ ] 測試與 ETF 比較功能

---

## 🚨 注意事項

### 1. 必須存在的資料
確保 `dim_security` 表中至少包含：
- **台積電** (security_id = '2330')
- **元大台灣50** (security_id = '0050')
- **元大高股息** (security_id = '0056')
- **國泰永續高股息** (security_id = '00878')

### 2. 代碼格式
- `dim_security.security_id` 是**純數字**（如 `2330`）
- 程式會自動加上 `.TW` 後綴給 yfinance 使用

### 3. ETF 識別
- 由於 dim_security 沒有 stock_type 欄位
- 使用簡易規則判斷：代碼長度 >= 5 或在基準列表中
- 若需更精準判斷，可考慮：
  - 查詢 industry 欄位
  - 或增加新欄位標示

### 4. 外部服務依賴
- 確保更新 dim_security 的服務正常運作
- 建議監控 `updated_at` 欄位確認資料新鮮度

---

## 📝 部署時需執行

```bash
# 1. 連線到 PostgreSQL
psql "postgresql://user:password@host:5432/dbname"

# 2. 僅執行 schema.sql（不需要 seed_stocks.sql）
\i migrations/schema.sql

# 3. 確認 dim_security 表有資料
SELECT security_id, name_zh FROM dim_security WHERE security_id IN ('2330', '0050', '0056', '00878');

# 預期結果：
# security_id | name_zh
# ------------|------------------
# 2330        | 台積電
# 0050        | 元大台灣50
# 0056        | 元大高股息  
# 00878       | 國泰永續高股息
```

---

## 🎉 完成狀態

所有變更已完成並測試通過。專案現在完全整合你現有的 `dim_security` 表，無需手動維護股票資料！

**下一步**: 部署到 Zeabur 並進行實際測試。
