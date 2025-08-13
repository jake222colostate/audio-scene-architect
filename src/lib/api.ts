export const join = (...parts: string[]): string => {
  return parts
    .filter(Boolean)
    .map((p, i) =>
      i === 0 ? p.replace(/\/+$|^\/+/g, "") : p.replace(/^\/+/g, "").replace(/\/+$/g, "")
    )
    .join("/");
};

const DEFAULT_API_BASE = (() => {
  if (typeof window !== "undefined") {
    if ((window as any).__API_BASE__) return (window as any).__API_BASE__;
    const baseEl = document.querySelector("base");
    const baseHref = baseEl?.getAttribute("href") || "";
    if (baseHref && !baseHref.startsWith("http")) {
      return `${window.location.origin}${baseHref.replace(/\/$/, "")}`;
    }
    return window.location.origin;
  }
  return "http://localhost:8000";
})();

export const API_BASE = import.meta.env.VITE_API_BASE || DEFAULT_API_BASE;

