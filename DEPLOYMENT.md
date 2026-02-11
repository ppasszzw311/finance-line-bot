# Finance LINE Bot

## 快速開始指南

### 1. 環境設定

```bash
# 1. 複製環境變數範例檔案
copy .env.example .env

# 2. 編輯 .env 填入以下資訊
# - LINE_CHANNEL_SECRET: 從 LINE Developers Console 取得
# - LINE_CHANNEL_ACCESS_TOKEN: 從 LINE Developers Console 取得
# - DATABASE_URL: PostgreSQL 連線字串（Zeabur 會自動提供）
```

### 2. 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 初始化資料庫（如果使用本地 PostgreSQL）
# 連線到 PostgreSQL 並執行：
psql -U postgres -d yourdb -f migrations/schema.sql
psql -U postgres -d yourdb -f migrations/seed_stocks.sql

# 或者使用 Python 初始化
python -c "from models.database import init_db; init_db()"

# 啟動開發伺服器
python main.py
# 或使用 uvicorn
uvicorn main:app --reload --port 8000
```

### 3. LINE Bot 設定

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 建立新的 Provider 和 Messaging API Channel
3. 在 Channel 設定中：
   - 取得 **Channel Secret** 和 **Channel Access Token**
   - 設定 Webhook URL: `https://your-domain.zeabur.app/webhook`
   - 啟用「Use webhook」
   - 關閉「Auto-reply messages」（避免干擾）
4. 將 Secret 和 Token 填入 `.env` 檔案

### 4. Zeabur 部署

#### 4-1. 建立專案

1. 登入 [Zeabur](https://zeabur.com)
2. 建立新專案
3. 新增服務：
   - 選擇 PostgreSQL（會自動設定 `DATABASE_URL`）
   - 部署此專案（連接 GitHub repo 或上傳程式碼）

#### 4-2. 設定環境變數

在 Zeabur 專案設定中新增環境變數：
```
LINE_CHANNEL_SECRET=你的_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=你的_access_token
```

`DATABASE_URL` 會由 PostgreSQL 服務自動注入。

#### 4-3. 初始化資料庫

**重要**: 本專案使用現有的 `dim_security` 表，該表應由外部服務維護。

```bash
# 連線到 Zeabur PostgreSQL
psql "postgresql://user:password@host:5432/dbname"

# 僅執行 schema 建立（不需要 seed_stocks.sql）
\i migrations/schema.sql

# 確認 dim_security 表存在且有資料
SELECT COUNT(*) FROM dim_security;
```

或者使用 Zeabur 的 SQL Editor 直接貼上執行 schema.sql。

**注意**: `dim_security` 表應包含：
- security_id (股票代碼，純數字如 2330)
- name_zh (中文名稱)
- market (市場別)
- 其他欄位請參考現有表結構

#### 4-4. 更新 LINE Webhook URL

部署完成後，取得 Zeabur 提供的域名（如 `https://your-app.zeabur.app`），
在 LINE Developers Console 更新 Webhook URL 為：
```
https://your-app.zeabur.app/webhook
```

點擊「Verify」測試連線。

### 5. 測試

1. 在 LINE 中搜尋你的 Bot（使用 QR Code 或 Bot ID）
2. 加入好友
3. 嘗試傳送訊息：
   ```
   買 2330 100股 250元
   ```
4. Bot 應該會回覆交易確認訊息

### 6. 常見問題排解

#### Q: Webhook 顯示連線失敗
- 檢查 Zeabur 服務是否正常運行
- 確認環境變數已正確設定
- 查看 Zeabur Logs 是否有錯誤訊息

#### Q: Bot 沒有回應
- 檢查 LINE Channel 的 Webhook 是否啟用
- 確認「Auto-reply messages」已關閉
- 查看 Zeabur Logs 確認是否收到 webhook

#### Q: 資料庫連線失敗
- 確認 `DATABASE_URL` 環境變數正確
- 檢查 PostgreSQL 服務是否運行
- 確認已執行 schema.sql

#### Q: 股價查詢失敗
- yfinance 可能受到 rate limit
- 可以稍後再試或考慮使用 FinMind API

### 7. 開發工具

```bash
# 測試手續費計算
python utils/fee_calculator.py

# 查看資料庫狀態
python -c "from models.database import engine; print(engine.table_names())"

# 測試訊息解析
python services/message_parser.py
```

### 8. 功能擴充建議

- [ ] Rich Menu 設計與上傳
- [ ] PostbackEvent 處理（按鈕互動）
- [ ] 歷史交易匯出（CSV）
- [ ] 股利記錄功能
- [ ] 價格提醒通知
- [ ] 圖表視覺化

### 9. 技術文件

- [LINE Messaging API 文件](https://developers.line.biz/en/docs/messaging-api/)
- [FastAPI 文件](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文件](https://docs.sqlalchemy.org/)
- [yfinance 文件](https://pypi.org/project/yfinance/)

### 10. 授權與貢獻

MIT License - 歡迎 PR 和 Issue！
