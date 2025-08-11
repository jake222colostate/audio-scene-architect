# Deploying to RunPod

- Use the stamped image tag printed by CI (not :latest), e.g. `jakeypoov/audio-scene-architect:cpu-YYYYMMDD-HHMMSS-<sha7>`.
- Expose port 8000.
- No env vars required. Optionally set PUBLIC_BASE_URL for absolute URLs.
- After changing image: Stop → Start the pod.
- Verify `/api/version`, then POST an 8–12s prompt to `/api/generate-audio`.
- SPA is served at `/` when present; generated audio under `/audio/*`.
