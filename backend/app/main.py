import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import webhook, admin, websocket

# Создаём директорию для логов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Формат логов
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Создаём файловый handler с немедленной записью
file_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
file_handler.setLevel(logging.INFO)

# Создаём консольный handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
console_handler.setLevel(logging.INFO)

# Настройка КОРНЕВОГО логгера - перехватывает ВСЕ логи
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []
root_logger.propagate = False
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Настройка логгеров uvicorn
for logger_name in ['uvicorn', 'uvicorn.error', 'uvicorn.access']:
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.handlers = []  # Убираем стандартные handlers
    uvicorn_logger.addHandler(file_handler)
    uvicorn_logger.addHandler(console_handler)
    uvicorn_logger.propagate = False  # Не дублировать в root

logger = logging.getLogger(__name__)
logger.info("🚀 Logging initialized - all logs will be written to file")

# Функция для немедленной записи логов
def flush_logs():
    """Принудительно сбрасывает буфер логов в файл"""
    for handler in logging.root.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()

settings = get_settings()

app = FastAPI(
    title="Khan Barbershop API",
    description="Backend API for Khan Barbershop WhatsApp chatbot with Alteegio integration",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    from app.database import init_db
    from app.services.broadcast_service import broadcast_service
    
    init_db()
    logger.info("✅ Database initialized")
    
    await broadcast_service.start()
    logger.info("✅ Broadcast service started")

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.broadcast_service import broadcast_service
    await broadcast_service.stop()
    logger.info("✅ Broadcast service stopped")

# CORS middleware for ManyChat
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook.router)
app.include_router(admin.router)
app.include_router(websocket.router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Khan Barbershop API"}


@app.post("/")
async def root_post(request: Request):
    """Handle misplaced POST requests - redirect to WhatsApp Cloud API webhook"""
    logger.warning("⚠️ POST request received at root. Redirecting to /webhook/whatsapp")
    return await webhook.whatsapp_webhook(request)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )