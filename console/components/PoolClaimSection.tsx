"use client";
// Sezione operatore: Pool (task liberi, claimabili da chiunque) + Le mie lavorazioni
// (task di cui sono titolare) con lifecycle BackOperation. Sta sopra la lista step nella
// pagina /lavorazioni. console_task_operator_view filtra server-side per operatore.
import { useCallback, useEffect, useState } from "react";
import {
  getOperatorTasks, claimTask, taskCheckin, taskCheckout, taskSign,
  type TaskCard, TASK_STATE_LABEL, nextAction,
} from "@/lib/lavboard";

export function PoolClaimSection() {
  const [pool, setPool] = useState<TaskCard[]>([]);
  const [mine, setMine] = useState<TaskCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await getOperatorTasks();
      if (r && Array.isArray(r.pool)) { setPool(r.pool); setMine(r.mine ?? []); }
      else setErr(r?.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading || err) return null; // silenzioso: la sezione step resta comunque utilizzabile
  if (!pool.length && !mine.length) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 560, margin: "0 auto", width: "100%" }}>
      {pool.length ? (
        <>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>Pool — task liberi ({pool.length})</div>
          {pool.map((c) => <TaskRow key={c.id} card={c} kind="pool" onDone={load} />)}
        </>
      ) : null}
      {mine.length ? (
        <>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>Le mie lavorazioni ({mine.length})</div>
          {mine.map((c) => <TaskRow key={c.id} card={c} kind="mine" onDone={load} />)}
        </>
      ) : null}
    </div>
  );
}

function TaskRow({ card, kind, onDone }: { card: TaskCard; kind: "pool" | "mine"; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const run = useCallback(async (fn: () => Promise<{ ok?: boolean; message?: string }>) => {
    setBusy(true); setMsg(null);
    try {
      const r = await fn();
      if (r && r.ok) onDone();
      else setMsg(r?.message ?? "errore");
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }, [onDone]);

  const next = nextAction(card);

  return (
    <div className="card" style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontWeight: 700, fontSize: 14 }}>{card.name}</div>
      <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
        <span className="chip" style={{ fontSize: 11 }}>{TASK_STATE_LABEL[card.state] ?? card.state}</span>
        {card.deadline ? <span className="muted" style={{ fontSize: 11 }}>⏰ {card.deadline.slice(0, 10)}</span> : null}
      </div>
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        {kind === "pool" ? (
          <button className="btn-primary" disabled={busy} onClick={() => run(() => claimTask(card.id))}>
            {busy ? "…" : "Prendi in carico"}
          </button>
        ) : (
          <>
            {next === "checkin" ? (
              <button className="btn-secondary" disabled={busy} onClick={() => run(() => taskCheckin(card.id))}>
                {busy ? "…" : "Check-in"}
              </button>
            ) : null}
            {next === "checkout" ? (
              <button className="btn-secondary" disabled={busy} onClick={() => run(() => taskCheckout(card.id))}>
                {busy ? "…" : "Check-out"}
              </button>
            ) : null}
            {next === "sign" ? (
              <button className="btn-primary" disabled={busy} onClick={() => run(() => taskSign(card.id))}>
                {busy ? "…" : "Firma e chiudi"}
              </button>
            ) : null}
          </>
        )}
      </div>
      {msg ? <div style={{ color: "var(--bad, #B23B3B)", fontSize: 13 }}>{msg}</div> : null}
    </div>
  );
}
