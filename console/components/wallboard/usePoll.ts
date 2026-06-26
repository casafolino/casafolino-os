"use client";
// Hook di polling client-side per i tile del wallboard.
// Sostituisce SWR (non in dipendenze) con un fetch + intervallo: auto-refresh
// senza ricaricare la pagina (kiosk h24). Rispetta visibilitychange (pausa in background).
import { useEffect, useRef, useState, useCallback } from "react";
import { BP } from "@/lib/basePath";
import { useFreshnessReport } from "@/components/wallboard/freshness";

export interface PollState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** epoch ms dell'ultimo fetch riuscito (null finché non arriva). */
  updatedAt: number | null;
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
  const [state, setState] = useState<PollState<T>>({ data: null, error: null, loading: true, updatedAt: null });
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const aborter = useRef<AbortController | null>(null);
  const report = useFreshnessReport();

  const fetchOnce = useCallback(async () => {
    aborter.current?.abort();
    const ac = new AbortController();
    aborter.current = ac;
    try {
      // l'endpoint può già contenere una querystring (es. "daily-goal?dept=logistica").
      const sep = endpoint.includes("?") ? "&" : "?";
      const url = `${BP}/api/wb/${endpoint}${sep}k=${encodeURIComponent(token)}`;
      const res = await fetch(url, { signal: ac.signal, cache: "no-store" });
      const json = (await res.json().catch(() => ({}))) as { ok?: boolean; message?: string };
      if (!res.ok || json.ok === false) {
        report?.(false, Date.now());
        setState((s) => ({ ...s, error: json.message ?? `HTTP ${res.status}`, loading: false }));
        return;
      }
      const ts = Date.now();
      report?.(true, ts);
      setState({ data: json as unknown as T, error: null, loading: false, updatedAt: ts });
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      report?.(false, Date.now());
      setState((s) => ({ ...s, error: (e as Error).message, loading: false }));
    }
  }, [endpoint, token, report]);

  useEffect(() => {
    if (!token) {
      setState({ data: null, error: "token-scena mancante (?k=)", loading: false, updatedAt: null });
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

/**
 * Feedback sui completamenti (mecc. E): rileva l'incremento di un contatore tra due
 * polling → flash verde 3s. Con prefers-reduced-motion il flash è disattivato (il
 * contatore resta comunque aggiornato dal chiamante).
 * @returns flash — true per ~3s dopo un incremento.
 */
export function useFlashOnIncrease(value: number | null | undefined): boolean {
  const prev = useRef<number | null>(null);
  const [flash, setFlash] = useState(false);
  useEffect(() => {
    if (value == null) return;
    const before = prev.current;
    prev.current = value;
    if (before == null || value <= before) return;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    setFlash(true);
    const id = setTimeout(() => setFlash(false), 3_000);
    return () => clearTimeout(id);
  }, [value]);
  return flash;
}

/** Emoji bandiera da codice ISO-2 (es. "DE" → 🇩🇪). Null-safe. */
export function flagEmoji(code: string | null | undefined): string {
  const c = (code ?? "").trim().toUpperCase();
  if (c.length !== 2 || !/^[A-Z]{2}$/.test(c)) return "";
  return String.fromCodePoint(...[...c].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
}
