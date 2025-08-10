import React, { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(8);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function gen() {
    setErr(null); setAudioUrl(null); setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/generate-audio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, duration })
      });
      const j = await r.json();
      if (!r.ok || !j.ok) throw new Error(j.error || r.statusText);
      setAudioUrl(j.file_url);
    } catch (e:any) { setErr(e.message || String(e)); }
    finally { setBusy(false); }
  }

  async function version() {
    const r = await fetch(`${API_BASE}/api/version`); setInfo(await r.json());
  }

  return (
    <div style={{ maxWidth: 720, margin: "32px auto", fontFamily: "system-ui, sans-serif" }}>
      <h1>SoundForge.AI</h1>
      <p>Enter a prompt and duration. The backend will try the heavy AudioGen model first, else a procedural fallback.</p>
      <div style={{ display: "grid", gap: 8 }}>
        <input placeholder="e.g., leaves crunching under footsteps" value={prompt} onChange={e=>setPrompt(e.target.value)} />
        <input type="number" min={1} max={120} value={duration} onChange={e=>setDuration(parseInt(e.target.value||"8"))} />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={gen} disabled={busy || !prompt.trim()}>{busy ? "Generating…" : "Generate"}</button>
          <button onClick={version}>/api/version</button>
        </div>
      </div>
      {err && <pre style={{ color: "crimson" }}>{err}</pre>}
      {audioUrl && <div style={{ marginTop: 16 }}>
        <audio src={audioUrl} controls />
        <div><a href={audioUrl} download>Download</a></div>
      </div>}
      {info && <details style={{ marginTop: 16 }} open>
        <summary>Version / Diagnostics</summary>
        <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(info, null, 2)}</pre>
      </details>}
    </div>
  );
}
