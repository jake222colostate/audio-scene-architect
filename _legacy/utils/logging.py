"""Logging utilities and structured logging helpers."""
import logging
import datetime
import traceback
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOG_FILE

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)
log = logging.getLogger(__name__)

# Structured logging helpers
def log_request(prompt: str, duration: int, filename: str):
    """Log incoming audio generation request."""
    log.info(f"[REQUEST] Prompt: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}' | Duration: {duration}s | File: {filename}")

def log_queue(action: str, filename: str, extra: str = ""):
    """Log queue operations."""
    log.info(f"[QUEUE] {action}: {filename}" + (f" | {extra}" if extra else ""))

def log_engine(action: str, detail: str = ""):
    """Log model engine operations."""
    log.info(f"[ENGINE] {action}" + (f" | {detail}" if detail else ""))

def log_export(action: str, filename: str, detail: str = ""):
    """Log file export operations."""
    log.info(f"[EXPORT] {action}: {filename}" + (f" | {detail}" if detail else ""))

def log_success(filename: str, detail: str = ""):
    """Log successful operations."""
    log.info(f"[SUCCESS] {filename}" + (f" | {detail}" if detail else ""))

def log_fail(filename: str, reason: str):
    """Log failed operations."""
    log.error(f"[FAIL] {filename} | Reason: {reason}")

def log_health(ram_mb: float, open_files: int, max_files: int):
    """Log system health status."""
    log.info(f"[HEALTH] RAM: {ram_mb:.0f}MB | Open files: {open_files}/{max_files}")

def log_error(tag: str, err: Exception) -> None:
    error_log = traceback.format_exc()
    logging.error(f"{tag}: {error_log}")
    
    # Write to both error log and main log
    with open("error_log.txt", "a") as f:
        f.write(f"[{datetime.datetime.now()}] {tag}\n")
        f.write(error_log + "\n")
    
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"[{timestamp}] ERROR - {tag}: {error_log}\n")