# Deploy to RunPod (GPU)

1. **Image**
   - Use the stamped tag printed by CI (e.g. `STAMPED_GPU_TAG`).
   - Do **not** use the `:latest` tag.

2. **Environment variables**
   - `USE_HEAVY=1`
   - `ALLOW_FALLBACK=1` *(set to `0` after the model loads successfully)*
   - `PUBLIC_BASE_URL=https://<RUNPOD_ID>-8000.proxy.runpod.net`
   - `HF_HOME=/app/.cache/huggingface`
   - `TRANSFORMERS_CACHE=/app/.cache/huggingface`
   - `AUDIO_OUT_DIR=/backend/output_audio`
   - `BUILD_TAG=<stamped tag>`

3. **Port**
   - Expose `8000`.

4. **Restart policy**
   - After changing image or env vars: **Stop** then **Start** the pod.

5. **Verification**
   - `GET /api/version` → `cuda_available:true`, correct `transformers`/`tokenizers` versions,
     `use_heavy_env:"1"`, `last_heavy_error:null`.
   - POST an 8–12s prompt to `/api/generate-audio` → response `generator:"heavy"` and audio plays.
