"""System health and resource monitoring utilities."""
import os
import psutil
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging import log, log_health

def check_system_health():
    """Check system resources before starting generation with structured logging."""
    try:
        # Check available memory (require at least 1.5GB)
        available_ram = psutil.virtual_memory().available / (1024 ** 2)  # in MB
        
        # Check open file handles
        try:
            current_process = psutil.Process()
            open_files = len(current_process.open_files())
            max_files = os.sysconf("SC_OPEN_MAX") if hasattr(os, 'sysconf') else 1024
        except (AttributeError, OSError):
            open_files = 0
            max_files = 1024
        
        # Log system health using structured logging
        log_health(available_ram, open_files, max_files)
        
        if available_ram < 1500:
            log.warning(f"⚠️ Low available RAM: {available_ram:.1f} MB")
            return False, f"Insufficient RAM: {available_ram:.1f}MB available, need 1500MB"
            
        if open_files > 0.9 * max_files:
            log.warning(f"⚠️ Too many open files: {open_files} / {max_files}")
            return False, f"Too many open files: {open_files}/{max_files}"
            
        return True, "System healthy"
        
    except Exception as e:
        log.error(f"System health check failed: {e}")
        return False, f"Health check failed: {str(e)}"

def _get_system_stats():
    """Helper function to get system statistics for health logging."""
    try:
        available_ram = psutil.virtual_memory().available / (1024 ** 2)
        current_process = psutil.Process()
        open_files = len(current_process.open_files())
        max_files = getattr(os, 'sysconf', lambda x: 1024)("SC_OPEN_MAX") if hasattr(os, 'sysconf') else 1024
        return available_ram, open_files, max_files
    except Exception:
        return 0.0, 0, 1024