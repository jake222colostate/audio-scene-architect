"""Model loading and management service."""
import traceback
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging import log, logger, log_health
from utils.system import _get_system_stats

# Global model storage for efficiency
_audiogen_model = None
_audioldm_model = None

try:
    from audiocraft.models import AudioGen
    import torch
    
    # GPU support for models
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[STARTUP] AudioCraft import successful - Using device: {device}")
except Exception as e:
    print(f"[STARTUP] ❌ AudioCraft import failed: {e}")
    raise RuntimeError("❌ AudioCraft is not installed or importable.")

try:
    import audioldm
    print("[STARTUP] AudioLDM import successful")
except ImportError:
    print("[STARTUP] AudioLDM not available - SFX generation will be limited")
    audioldm = None

def get_audiogen_model():
    """Get or initialize the global AudioGen model with comprehensive error handling."""
    global _audiogen_model
    if _audiogen_model is None:
        try:
            # Check system resources before loading model
            log_health(*_get_system_stats())
            
            log.info("[MODEL] Starting AudioGen model load: facebook/audiogen-medium")
            log.info("[MODEL] Importing audiocraft.models.AudioGen...")
            
            from audiocraft.models import AudioGen
            
            log.info("[MODEL] Calling AudioGen.get_pretrained()...")
            log.info("[MODEL] This may take 30-60 seconds for initial download...")
            
            _audiogen_model = AudioGen.get_pretrained("facebook/audiogen-medium").to(device)
            logger.info(f"✅ AudioGen model loaded on {device}")
            
            # Validate model was loaded successfully
            if _audiogen_model is None:
                raise RuntimeError("Model initialization returned None")
            
            log.info("[MODEL] ✓ AudioGen model loaded successfully")
            log.info(f"[MODEL] Model device: {_audiogen_model.device if hasattr(_audiogen_model, 'device') else 'Unknown'}")
            log.info(f"[MODEL] Model sample rate: {_audiogen_model.compression_model.cfg.sample_rate if hasattr(_audiogen_model, 'compression_model') else 'Unknown'}")
            
        except ImportError as e:
            log.error(f"[MODEL FAIL] AudioCraft import failed: {str(e)}")
            log.error("[MODEL FAIL] Ensure audiocraft is installed: pip install -e git+https://github.com/facebookresearch/audiocraft.git#egg=audiocraft")
            raise RuntimeError("❌ AudioCraft dependency missing. Check installation.")
        except torch.cuda.OutOfMemoryError as e:
            log.error(f"[MODEL FAIL] CUDA out of memory: {str(e)}")
            log.error("[MODEL FAIL] Try using a larger GPU or reducing batch size")
            raise RuntimeError("❌ GPU memory insufficient for AudioGen model")
        except Exception as e:
            if "T5EncoderModel" in str(e):
                log.error(
                    "[MODEL FAIL] Missing dependency 'transformers' (T5EncoderModel). "
                    "Install heavy requirements: pip install -r backend/requirements-heavy.txt"
                )
            log.error(f"[MODEL FAIL] AudioGen load failed: {str(e)}")
            log.error(f"[MODEL FAIL] Full error: {traceback.format_exc()}")
            log.error("[MODEL FAIL] Possible causes:")
            log.error("[MODEL FAIL] - Insufficient RAM (need 4GB+ available)")
            log.error("[MODEL FAIL] - Corrupted model cache (delete ~/.cache/huggingface)")
            log.error("[MODEL FAIL] - PyTorch version mismatch")
            log.error("[MODEL FAIL] - Network issues during model download")
            raise RuntimeError("❌ AudioGen model failed to load. Check logs for details.")
    return _audiogen_model

def get_audioldm_model():
    """Get or initialize the global AudioLDM model."""
    global _audioldm_model
    if _audioldm_model is None and audioldm is not None:
        try:
            log.info("Loading AudioLDM model globally...")
            # Try GPU first, fallback to CPU
            try:
                _audioldm_model = audioldm.AudioLDM()
                log.info("✓ AudioLDM model loaded with GPU")
            except Exception as gpu_error:
                log.warning(f"GPU loading failed: {gpu_error}, trying CPU...")
                _audioldm_model = audioldm.AudioLDM(use_cpu=True)
                log.info("✓ AudioLDM model loaded with CPU")
        except Exception as e:
            log.error(f"Failed to load AudioLDM model: {e}")
            raise
    return _audioldm_model