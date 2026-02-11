# LINE Bot 股票投資記錄系統

一個基於 LINE Bot 的個人投資組合追蹤系統，支援自然語言輸入交易記錄、查詢持股、計算損益、以及比較不同投資人的績效表現。

## 核心功能

1. **📝 記錄交易** - 支援自然語言輸入買賣記錄
   - 「買 2330 100股 250元」
   - 「小明賣鴻海200股 價格120」

2. **💼 持股查詢** - 查看自己或朋友的持股狀況
   - 即時股價與未實現損益
   - 平均成本計算

3. **💰 損益報告** - 已實現與未實現損益統計
   - 自動計算手續費與證交稅
   - 詳細交易歷史

4. **📊 績效比較** - 與朋友或 ETF 比較投資績效
   - 支援 0050、0056、00878 等熱門 ETF
   - 排行榜功能

## 技術架構

- **後端框架**: FastAPI (Python 3.11+)
- **資料庫**: PostgreSQL
- **部署平台**: Zeabur
- **LINE SDK**: line-bot-sdk-python
- **股價資料**: yfinance
- **股票資料**: 使用現有 dim_security 表（每日自動更新）

## 專案結構

```
finance-line-bot/
├── main.py                 # FastAPI 主程式
├── models/
│   ├── database.py         # SQLAlchemy 資料庫模型
│   └── schemas.py          # Pydantic 資料驗證
├── services/
│   ├── line_handler.py     # LINE webhook 處理
│   ├── message_parser.py   # 自然語言解析
│   ├── transaction_service.py  # 交易邏輯
│   ├── portfolio_service.py    # 持股計算
│   ├── stock_service.py    # 股價查詢
│   └── comparison_service.py   # 績效比較
├── utils/
│   ├── fee_calculator.py   # 手續費計算
│   └── message_builder.py  # LINE Flex Message
├── migrations/
    ├── schema.sql          # 資料庫結構
    └── seed_stocks.sql     # 說明文件（使用現有 dim_security）
```

## 安裝與部署

### 1. 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 LINE Bot 資訊與資料庫連線

# 初始化資料庫
# 注意：本專案使用現有的 dim_security 表，請確保該表已存在
psql -U postgres -d yourdb -f migrations/schema.sql

# 啟動服務
uvicorn main:app --reload
```

### 2. Zeabur 部署

1. 在 Zeabur 建立新專案
2. 新增 PostgreSQL 服務（注意：確保已有 dim_security 表）
3. 連線至 PostgreSQL 執行 `schema.sql`
4. 部署此專案（自動偵測為 Python）
5. 設定環境變數：
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `DATABASE_URL` (由 Zeabur 自動提供)
6. 在 LINE Developers Console 設定 Webhook URL: `https://your-app.zeabur.app/webhook`

**重要**: 本專案依賴現有的 `dim_security` 表，該表應由外部服務每日自動更新台股資料。

## 使用方式

### 記錄交易

直接在 LINE 對話框輸入：
- `買 2330 100股 250元` - 記錄自己買入台積電
- `我買台積電 50股 @600` - 另一種輸入格式
- `小明賣鴻海200股 價格120` - 記錄朋友小明的交易

### Rich Menu 功能

點擊底部選單：
- **📝 記錄交易** - 引導式輸入
- **💼 我的持股** - 查看自己的持股
- **👥 朋友持股** - 查看朋友持股
- **💰 損益報告** - 詳細損益分析
- **📊 績效比較** - 與他人或 ETF 比較
- **❓ 使用說明** - 查看指令說明

## 資料模型說明

### 核心概念

此系統採用「個人觀察帳本」模式：
- 每位 LINE 用戶擁有獨立帳本
- 可記錄自己及朋友的投資活動
- 所有記錄基於用戶自己的輸入，資料不跨用戶同步
- 例如：你記錄「小明買100股」，小明本人記錄「我買300股」，兩者獨立不衝突

### 手續費計算

- **買入手續費**: 交易金額 × 0.1425%
- **賣出手續費**: 交易金額 × 0.1425%
- **證交稅**: 賣出金額 × 0.3%（僅賣出時收取）

### 平均成本法

持股成本採用加權平均：
```
新平均成本 = (原持股成本 × 原股數 + 新買入總額) ÷ (原股數 + 新買入股數)
```

## 開發團隊

Developer: Pablo

## 授權

MIT License

## 聯絡方式

如有問題或建議，請透過 Issues 回報。
