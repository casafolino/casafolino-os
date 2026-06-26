"use client";
// Freschezza dati di scena: i tile (via usePoll) riportano qui l'esito di ogni fetch.
// FreshnessBadge mostra "aggiornato Ns fa"; giallo se l'ultimo fetch è fallito o stale.
import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";

interface FreshnessState {
  lastOkTs: number | null;
  lastError: boolean;
}
interface FreshnessApi extends FreshnessState {
  report: (ok: boolean, ts: number) => void;
  /** un tile segnala uno stato d'allarme attivo (per la pausa rotazione). */
  reportAlert: (key: string, active: boolean) => void;
  alertCount: number;
}

const Ctx = createContext<FreshnessApi | null>(null);

/** Soglia di staleness: oltre questo dall'ultimo successo → giallo. */
const STALE_MS = 90_000;

export function FreshnessProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<FreshnessState>({ lastOkTs: null, lastError: false });
  const [alertCount, setAlertCount] = useState(0);
  const alerts = useRef<Set<string>>(new Set());
  const report = useCallback((ok: boolean, ts: number) => {
    setState((s) => (ok ? { lastOkTs: ts, lastError: false } : { ...s, lastError: true }));
  }, []);
  const reportAlert = useCallback((key: string, active: boolean) => {
    const set = alerts.current;
    const had = set.has(key);
    if (active && !had) set.add(key);
    else if (!active && had) set.delete(key);
    else return;
    setAlertCount(set.size);
  }, []);
  return <Ctx.Provider value={{ ...state, report, reportAlert, alertCount }}>{children}</Ctx.Provider>;
}

/** Hook interno: i tile chiamano report() ad ogni fetch (no-op fuori dal provider). */
export function useFreshnessReport() {
  return useContext(Ctx)?.report;
}

/** Un tile dichiara il proprio stato d'allarme; aggiorna il provider (no-op se fuori). */
export function useReportAlert(key: string, active: boolean) {
  const ctx = useContext(Ctx);
  useEffect(() => {
    ctx?.reportAlert(key, active);
    return () => ctx?.reportAlert(key, false);
  }, [ctx, key, active]);
}

/** True se almeno un tile della scena è in allarme (usato per pausa rotazione). */
export function useAlertActive(): boolean {
  return (useContext(Ctx)?.alertCount ?? 0) > 0;
}

export function FreshnessBadge() {
  const ctx = useContext(Ctx);
  const [, tick] = useState(0);
  // ridisegna ogni 2s per far avanzare "Ns fa".
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 2_000);
    return () => clearInterval(id);
  }, []);
  if (!ctx) return null;
  const now = Date.now();
  const secs = ctx.lastOkTs ? Math.round((now - ctx.lastOkTs) / 1000) : null;
  const stale = ctx.lastError || ctx.lastOkTs == null || now - (ctx.lastOkTs ?? 0) > STALE_MS;
  const label = secs == null ? "in attesa…" : stale ? "dati non aggiornati" : `aggiornato ${secs}s fa`;
  return (
    <span className={`wb-fresh${stale ? " stale" : ""}`} title={label}>
      <span className="wb-fresh-dot" />
      {label}
    </span>
  );
}
