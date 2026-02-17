import logging
import sys
from pathlib import Path

# Создаём папку для логов, если её нет
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Настройка логирования
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler("logs/xlog.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("xlog")