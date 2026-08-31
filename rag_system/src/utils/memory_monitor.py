# src/utils/memory_monitor.py
import torch
import gc
import os
from .logger import setup_logger

logger = setup_logger(__name__)

class MemoryMonitor:
    """Memory monitoring utility"""

    @staticmethod
    def get_gpu_memory():
        """Get GPU memory usage"""
        if torch.cuda.is_available():
            try:
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                max_allocated = torch.cuda.max_memory_allocated() / 1024**3
                return {
                    'allocated': allocated,
                    'reserved': reserved,
                    'max_allocated': max_allocated,
                    'total': torch.cuda.get_device_properties(0).total_memory / 1024**3
                }
            except Exception as e:
                logger.warning(f"Failed to get GPU memory info: {e}")
                return None
        return None

    @staticmethod
    def get_system_memory():
        """Get system memory usage"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                'total': mem.total / 1024**3,
                'available': mem.available / 1024**3,
                'used': mem.used / 1024**3,
                'percent': mem.percent
            }
        except ImportError:
            return {'total': 0, 'available': 0, 'used': 0, 'percent': 0}
        except Exception as e:
            logger.warning(f"Failed to get system memory info: {e}")
            return {'total': 0, 'available': 0, 'used': 0, 'percent': 0}

    @staticmethod
    def cleanup():
        """Clean up memory"""
        gc.collect()
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            except Exception as e:
                logger.warning(f"GPU cache cleanup failed: {e}")
        logger.info("Memory cleanup complete")

    @staticmethod
    def log_status(tag=""):
        """Log the current memory status"""
        try:
            system = MemoryMonitor.get_system_memory()
            gpu = MemoryMonitor.get_gpu_memory()

            if system and system['total'] > 0:
                msg = f"[{tag}] System memory: {system['used']:.1f}GB/{system['total']:.1f}GB ({system['percent']:.1f}%)"
            else:
                msg = f"[{tag}] System memory: N/A"

            if gpu:
                msg += f" | GPU: {gpu['allocated']:.2f}GB/{gpu['total']:.2f}GB"

            logger.info(msg)
            return system, gpu
        except Exception as e:
            logger.warning(f"Failed to log memory status: {e}")
            return None, None

def cleanup_memory():
    """Global memory cleanup function"""
    MemoryMonitor.cleanup()
    MemoryMonitor.log_status("After cleanup")
