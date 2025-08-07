"""Audio generation service with all audio processing logic."""
import os
import uuid
import datetime
import traceback
import torchaudio
import whisper
from pydub import AudioSegment
try:
    import torchaudio
except Exception:
    torchaudio = None
try:
    import whisper
except Exception:
    whisper = None
from pydub.generators import Sine, WhiteNoise

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.model_manager import get_audiogen_model, get_audioldm_model, audioldm
from utils.logging import log, logger, log_error
from utils.system import check_system_health
from config import OUTPUT_DIR, LOG_FILE

def _generate_procedural_ambience(prompt: str, duration: int) -> AudioSegment:
    dur_ms = max(1000 * int(duration), 10000)
    base = WhiteNoise().to_audio_segment(duration=dur_ms).apply_gain(-28)
    hum1 = Sine(55).to_audio_segment(duration=dur_ms).apply_gain(-16)
    hum2 = Sine(110).to_audio_segment(duration=dur_ms).apply_gain(-20)
    sweep = Sine(440).to_audio_segment(duration=dur_ms).fade_in(1500).fade_out(1500).apply_gain(-26)
    mix = base.overlay(hum1).overlay(hum2).overlay(sweep)
    mix = mix.set_frame_rate(44100).set_channels(2)
    return mix



def generate_audio_from_text(prompt: str, duration: int, filename: str) -> None:
    """Generate audio using AudioGen with comprehensive error handling and structured logging."""
    try:
        log.info(f"[GENERATION] Starting audio generation for: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'")
        log.info(f"[GENERATION] Duration: {duration}s | Output: {filename}")
        
        # System health check
        healthy, health_msg = check_system_health()
        if not healthy:
            raise RuntimeError(f"System health check failed: {health_msg}")
        
        # Get the model (handles loading if needed)
        try:
            log.info("[GENERATION] Loading AudioGen model...")
            model = get_audiogen_model()
            log.info("[GENERATION] ✓ AudioGen model ready")
        except Exception as e:
            error_msg = f"Model loading failed: {str(e)}"
            log_error("MODEL_LOAD_FAIL", e)
            raise RuntimeError(error_msg)
        
        # Set model parameters
        try:
            log.info(f"[GENERATION] Setting model duration to {duration} seconds")
            model.set_generation_params(duration=duration)
            log.info("[GENERATION] ✓ Model parameters set")
        except Exception as e:
            error_msg = f"Model parameter setup failed: {str(e)}"
            log_error("MODEL_PARAM_FAIL", e)
            raise RuntimeError(error_msg)
        
        # Generate audio
        try:
            log.info(f"[GENERATION] Generating audio with prompt: '{prompt}'")
            log.info("[GENERATION] This may take 30-60 seconds...")
            
            wav = model.generate([prompt])
            log.info(f"[GENERATION] ✓ Audio tensor generated. Shape: {wav.shape}")
        except Exception as e:
            error_msg = f"Audio generation failed: {str(e)}"
            log_error("AUDIO_GEN_FAIL", e)
            raise RuntimeError(error_msg)
        
        # Save audio file
        try:
            output_path = OUTPUT_DIR / filename
            log.info(f"[GENERATION] Saving audio to: {output_path}")
            
            # Ensure the audio tensor is on CPU and has the right shape
            wav_cpu = wav[0].detach().cpu()  # AudioGen returns list, take first item
            if wav_cpu.dim() == 3:
                wav_cpu = wav_cpu.squeeze(0)  # Remove batch dimension
            
            # Save using torchaudio
            sample_rate = model.compression_model.cfg.sample_rate
            torchaudio.save(str(output_path), wav_cpu, sample_rate, format="mp3")
            
            # Verify file was created and has reasonable size
            if not output_path.exists():
                raise RuntimeError("Output file was not created")
            
            file_size = output_path.stat().st_size
            if file_size < 1000:  # Less than 1KB is suspicious
                raise RuntimeError(f"Output file is too small: {file_size} bytes")
            
            log.info(f"[GENERATION] ✅ Audio saved successfully")
            log.info(f"[GENERATION] File size: {file_size / 1024:.1f} KB")
            log.info(f"[GENERATION] Sample rate: {sample_rate} Hz")
            
        except Exception as e:
            error_msg = f"Audio file save failed: {str(e)}"
            log_error("AUDIO_SAVE_FAIL", e)
            raise RuntimeError(error_msg)
            
    except Exception as e:
        # Final catch-all error handler
        error_msg = f"Audio generation pipeline failed: {str(e)}"
        full_trace = traceback.format_exc()
        log_error("GENERATION_PIPELINE_FAIL", e)
        
        # Write comprehensive error log
        try:
            with open(LOG_FILE, "a") as logf:
                timestamp = datetime.datetime.now().isoformat()
                logf.write(f"[{timestamp}] GENERATION_FAILED: {filename}\n")
                logf.write(f"Prompt: {prompt}\n")
                logf.write(f"Duration: {duration}\n")
                logf.write(f"Error: {error_msg}\n")
                logf.write(f"Full traceback:\n{full_trace}\n\n")
        except Exception:
            pass  # Don't let log writing errors crash the error handler
        
        # Re-raise with comprehensive error message
        raise RuntimeError(f"Generation failed for '{filename}': {error_msg}")

def transcribe_video(filepath: str) -> str:
    """Extract audio using ffmpeg and transcribe with Whisper."""
    model = whisper.load_model("base")
    audio_path = filepath.rsplit(".", 1)[0] + ".wav"
    os.system(
        f"ffmpeg -y -i {filepath} -ar 16000 -ac 1 {audio_path} >/dev/null 2>&1"
    )
    result = model.transcribe(audio_path)
    return result.get("text", "")

def analyze_tone(transcript: str) -> str:
    """Return a simple tone classification from the transcript."""
    transcript = transcript.lower()
    if any(w in transcript for w in ["run", "hide", "scared", "no", "stop"]):
        return "fear"
    if any(w in transcript for w in ["angry", "mad", "fight", "kill"]):
        return "aggression"
    if any(w in transcript for w in ["alone", "quiet", "lost"]):
        return "isolation"
    return "neutral"

def generate_sfx_clip(prompt: str, duration: int) -> str | None:
    try:
        log.info(f"[SFX] Starting SFX generation for: '{prompt}', duration: {duration}s")
        
        # Initialize AudioLDM model
        if audioldm is None:
            log.error("[SFX] AudioLDM not available - module not imported")
            return None
        
        try:
            log.info("[SFX] Getting AudioLDM model...")
            model = get_audioldm_model()
            log.info("[SFX] AudioLDM model ready")
        except Exception as e:
            error_msg = f"[SFX] Failed to get AudioLDM model: {str(e)}"
            error_log = traceback.format_exc()
            log.error(f"{error_msg}\n{error_log}")
            
            # Write to log file
            with open(LOG_FILE, "a") as log_file:
                timestamp = datetime.datetime.now().isoformat()
                log_file.write(f"[{timestamp}] SFX_MODEL_ERROR: {error_msg}\n{error_log}\n")
            return None
        
        # Generate audio
        try:
            log.info(f"[SFX] Generating audio for prompt: '{prompt}'")
            audio = model.generate(prompt=prompt, duration=duration)
            log.info(f"[SFX] Audio tensor generated successfully. Shape: {audio.shape if hasattr(audio, 'shape') else 'Unknown'}")
        except Exception as e:
            error_msg = f"[SFX] Audio generation failed: {str(e)}"
            error_log = traceback.format_exc()
            log.error(f"{error_msg}\n{error_log}")
            
            with open(LOG_FILE, "a") as log_file:
                timestamp = datetime.datetime.now().isoformat()
                log_file.write(f"[{timestamp}] SFX_GENERATION_ERROR: {error_msg}\n{error_log}\n")
            return None
        
        # Save the generated audio
        try:
            output_filename = f"sfx_{uuid.uuid4().hex}.wav"
            output_path = OUTPUT_DIR / output_filename
            
            log.info(f"[SFX] Saving SFX audio to: {output_path}")
            
            # Save using torchaudio (assuming audio is a torch tensor)
            if hasattr(audio, 'detach'):
                audio_cpu = audio.detach().cpu()
                if audio_cpu.dim() == 3:
                    audio_cpu = audio_cpu.squeeze(0)
                torchaudio.save(str(output_path), audio_cpu, sample_rate=16000, format="wav")
            else:
                # Fallback for numpy arrays or other formats
                import soundfile as sf
                sf.write(str(output_path), audio, 16000)
            
            log.info(f"[SFX] ✅ SFX audio saved: {output_filename}")
            return str(output_path)
            
        except Exception as e:
            error_msg = f"[SFX] Failed to save SFX audio: {str(e)}"
            error_log = traceback.format_exc()
            log.error(f"{error_msg}\n{error_log}")
            
            with open(LOG_FILE, "a") as log_file:
                timestamp = datetime.datetime.now().isoformat()
                log_file.write(f"[{timestamp}] SFX_SAVE_ERROR: {error_msg}\n{error_log}\n")
            return None
            
    except Exception as e:
        error_msg = f"[SFX] Unexpected error in SFX generation: {str(e)}"
        error_log = traceback.format_exc()
        log.error(f"{error_msg}\n{error_log}")
        
        with open(LOG_FILE, "a") as log_file:
            timestamp = datetime.datetime.now().isoformat()
            log_file.write(f"[{timestamp}] SFX_UNEXPECTED_ERROR: {error_msg}\n{error_log}\n")
        return None