
# Line的查詢買賣持股紀錄機器人
既然你的主要考量是**「朋友都在 LINE 上」**，那選擇 LINE Bot 絕對是正確的決定。因為強迫朋友為了你的機器人下載 Discord 的門檻太高，在 LINE 上他們只要點個連結就能開始記帳。

針對 LINE Bot 的開發，我為你規劃了一套最適合新手的技術路線：

1. 推薦程式語言：Python
雖然 LINE 支持多種語言（Node.js, Go, Java, PHP），但我強烈建議你使用 Python，原因有三：

金融套件豐富： Python 有 yfinance 或 FinMind 等強大工具，抓取台股現價只需要兩行程式碼。

社群資源： 台灣開發 LINE Bot 的教學文章，約有 70% 都是用 Python 寫的，遇到問題很容易找到答案。

語法直覺： 適合處理你提到的「解析對話內容（NLP）」邏輯。

2. 技術架構規劃 (The Tech Stack)
為了讓你的記帳機器人跑起來，你需要這四個組件：

框架 (Framework): Flask 或 FastAPI。

這就像是機器人的「大腦」，負責接收 LINE 傳過來的訊息並決定怎麼回覆。

資料庫 (Database): Google Sheets (試算表) 或 PostgreSQL。

新手推薦： 先串接 Google Sheets。優點是你可以直接打開 Excel 介面看朋友的買賣紀錄，不用寫 SQL 指令。

部署環境 (Hosting): Render 或 PythonAnywhere。

機器人程式需要一台 24 小時不關機的電腦執行。

爬蟲/API (Finance API): yfinance。

用來查詢鴻海、華邦電現在到底多少錢，好計算損益。

3. 開發路線圖 (Step-by-Step)
第一階段：基礎串接 (Hello World)
去 LINE Developers 註冊一個 Messaging API 帳號。

安裝 Python 並使用官方提供的 line-bot-sdk-python。

實作「鸚鵡功能」：你傳什麼給它，它就回什麼。

第二階段：資料記帳 (The Brain)
解析文字： 寫一段邏輯去判斷這句話有沒有包含「買」、「賣」、「股」等關鍵字。

串接 Google Sheets： 使用 gspread 套件。當機器人聽到「買入」時，就把資料寫入試算表的一格。

第三階段：查詢損益 (The Value)
實作查詢功能：當使用者說「查詢損益」。

程式去試算表抓出「買入價格」。

程式去 yfinance 抓出「目前股價」。

相減後透過 LINE 的 Flex Message（像網購清單那種漂亮的卡片）傳回給朋友。

4. 給你的第一個小建議
LINE 有一個很棒的功能叫 Rich Menu (圖文選單)。 既然是為了記帳，你可以設計選單按鈕：

[按鈕 A]：查看我的持股

[按鈕 B]：今日即時損益

[按鈕 C]：記帳說明

這樣你朋友就不用每次都打字，點一下就能看到結果。

你想先從哪一部分開始？ 我可以先幫你寫一段 Python 程式碼範例，示範如何從「我買了鴻海300股 價格221元」這句話中提取出股票名稱和數字。