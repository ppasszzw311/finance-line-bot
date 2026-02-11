"""
LINE Bot Finance Tracker - Main Application
"""
import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FollowEvent
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.database import get_db, init_db
from services.line_handler import LineHandler, handler as webhook_handler

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 應用程式
app = FastAPI(
    title="LINE Bot Finance Tracker",
    description="股票投資記錄與損益分析 LINE Bot",
    version="1.0.0"
)

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE Bot credentials not found in environment variables!")


@app.on_event("startup")
async def startup_event():
    """應用程式啟動時執行"""
    logger.info("Starting LINE Bot Finance Tracker...")
    logger.info(f"PORT: {os.getenv('PORT', '8080')}")
    # 初始化資料庫（如果需要）
    # init_db()  # 注意：在 Zeabur 上應該已經執行過 schema.sql


@app.get("/")
async def root():
    """根路徑 - API 資訊"""
    return {
        "service": "LINE Bot Finance Tracker",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    LINE Bot Webhook 端點
    
    接收來自 LINE Platform 的事件通知
    """
    # 取得 signature 和 body
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    body_text = body.decode('utf-8')
    
    logger.info(f"Webhook received. Signature: {signature[:10]}...")
    
    try:
        # 驗證簽章並處理事件
        webhook_handler.handle(body_text, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Check your channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return JSONResponse(content={"status": "ok"})


# 註冊 LINE 事件處理器
@webhook_handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息事件"""
    # 建立資料庫 session
    from models.database import get_session_maker
    SessionLocal = get_session_maker()
    db = SessionLocal()
    
    try:
        line_handler = LineHandler(db)
        line_handler.handle_text_message(event)
    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
    finally:
        db.close()


@webhook_handler.add(FollowEvent)
def handle_follow(event):
    """處理用戶加入好友事件"""
    from models.database import get_session_maker
    SessionLocal = get_session_maker()
    db = SessionLocal()
    
    try:
        line_handler = LineHandler(db)
        line_handler.handle_follow(event)
    except Exception as e:
        logger.error(f"Error in handle_follow: {e}")
    finally:
        db.close()


# 錯誤處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全域錯誤處理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on port {port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
