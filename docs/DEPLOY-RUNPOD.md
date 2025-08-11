# Deploy to RunPod (GPU)

**Image**: use the printed `STAMPED_GPU_TAG` (not `:latest`).

**Port**: `8000`

**Env vars (set in RunPod):**

```
USE_HEAVY=1
ALLOW_FALLBACK=1 # set to 0 after confirming heavy loads
AUDIOGEN_MODEL=facebook/audiogen-medium
PUBLIC_BASE_URL=https://<RUNPOD_ID>-8000.proxy.runpod.net
AUDIO_OUT_DIR=/app/backend/output_audio
HF_HOME=/app/.cache/huggingface
TRANSFORMERS_CACHE=/app/.cache/huggingface
BUILD_TAG=<paste stamped tag>
IMAGE_TAG=<paste stamped tag>
```

**Restart**: Stop → Start the pod after changing the image/env.

**Verify:**

- `GET /api/version` shows `cuda_available:true`, correct versions, `heavy_loaded:true`, `last_heavy_error:null`.
- Generate an 8–12s prompt; JSON shows `"generator":"heavy"` and audio plays.
