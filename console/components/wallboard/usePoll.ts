"use client";
// Hook di polling client-side per i tile del wallboard.
// Sostituisce SWR (non in dipendenze) con un fetch + intervallo: auto-refresh
// senza ricaricare la pagina (kiosk h24). Rispetta visibilitychange (pausa in background).
import { useEffect, useRef, useState, useCallback } from "react";
import { BP } from "@/lib/basePath";

export interface PollState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * @param endpoint nome endpoint sotto /api/wb (es. "mrp-active")
 * @param token    token-scena (?k=)
 * @param intervalMs intervallo refresh
 */
export function usePoll<T = Record<string, unknown>>(
  endpoint: string,
  token: string,
  intervalMs: number,
): PollState<T> {
  const [state, setState] = useState<PollState<T>>({ data: null, error: null, loading: true });
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const aborter = useRef<AbortController | null>(null);

  const fetchOnce = useCallback(async () => {
    aborter.current?.abort();
    const ac = new AbortController();
    aborter.current = ac;
    try {
      const url = `${BP}/api/wb/${endpoint}?k=${encodeURIComponent(token)}`;
      const res = await fetch(url, { signal: ac.signal, cache: "no-store" });
      const json = (await res.json().catch(() => ({}))) as { ok?: boolean; message?: string };
      if (!res.ok || json.ok === false) {
        setState((s) => ({ data: s.data, error: json.message ?? `HTTP ${res.status}`, loading: false }));
        return;
      }
      setState({ data: json as unknown as T, error: null, loading: false });
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setState((s) => ({ data: s.data, error: (e as Error).message, loading: false }));
    }
  }, [endpoint, token]);

  useEffect(() => {
    if (!token) {
      setState({ data: null, error: "token-scena mancante (?k=)", loading: false });
      return;
    }
    fetchOnce();
    timer.current = setInterval(() => {
      if (document.visibilityState === "visible") fetchOnce();
    }, intervalMs);
    const onVis = () => {
      if (document.visibilityState === "visible") fetchOnce();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      if (timer.current) clearInterval(timer.current);
      document.removeEventListener("visibilitychange", onVis);
      aborter.current?.abort();
    };
  }, [fetchOnce, intervalMs, token]);

  return state;
}

/** Emoji bandiera da codice ISO-2 (es. "DE" → 🇩🇪). Null-safe. */
export function flagEmoji(code: string | null | undefined): string {
  const c = (code ?? "").trim().toUpperCase();
  if (c.length !== 2 || !/^[A-Z]{2}$/.test(c)) return "";
  return String.fromCodePoint(...[...c].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
}
