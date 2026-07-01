"use client";
// Board Lavorazioni per-assegnatario + Pool (vista manager). Colonne = Pool + una per
// operativa. Legge cf.task via console_task_board (manager-gated server-side). Azioni:
// assegna (pool→persona / persona→pool), claim, e lifecycle BackOperation
// (check-in → check-out → firma). Refetch dopo ogni azione (come StepCard).
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getTaskBoard, claimTask, taskCheckin, taskCheckout, taskSign, assignTask,
  type TaskBoard as TBoard, type TaskCard, type TaskColumn,
  TASK_STATE_LABEL, columnAccent, nextAction,
} from "@/lib/lavboard";

export function TaskBoard() {
  const [board, setBoard] = useState<TBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const b = await getTaskBoard();
      if (b && Array.isArray(b.columns)) setBoard(b);
      else setErr(b?.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const assignees = useMemo(
    () => (board?.columns ?? [])
      .filter((c) => c.kind === "assignee" && typeof c.employeeId === "number")
      .map((c) => ({ id: c.employeeId as number, name: c.name })),
    [board],
  );

  if (loading) return <div className="muted" style={{ padding: 16 }}>Carico…</div>;
  if (err) return <div style={{ padding: 16, color: "var(--bad, #B23B3B)" }}>Errore: {err}</div>;
  if (!board) return null;

  return (
    <div style={{ display: "flex", gap: 11, alignItems: "flex-start", overflowX: "auto", paddingBottom: 8 }}>
      {board.columns.map((col) => (
        <div key={col.key} className="grow" style={{ minWidth: 244 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 9, padding: "0 4px" }}>
            <span className="row" style={{ gap: 7, fontWeight: 600, fontSize: 13 }}>
              <span style={{ width: 9, height: 9, borderRadius: 3, background: columnAccent(col), display: "inline-block" }} />
              {col.name}
            </span>
            <span className="muted" style={{ fontSize: 11 }}>{col.count}</span>
          </div>
          {col.cards.length === 0 ? (
            <div className="empty-honest" style={{ fontSize: 12 }}>
              <span>{col.kind === "pool" ? "Pool vuoto." : "Nessun task in coda."}</span>
            </div>
          ) : (
            col.cards.map((card) => (
              <TaskCardView
                key={card.id}
                card={card}
                column={col}
                assignees={assignees}
                onDone={load}
              />
            ))
          )}
        </div>
      ))}
    </div>
  );
}

function TaskCardView({
  card, column, assignees, onDone,
}: {
  card: TaskCard;
  column: TaskColumn;
  assignees: { id: number; name: string }[];
  onDone: () => void;
}) {
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

  const accent = columnAccent(column);
  const next = nextAction(card);
  const overdue = card.deadline && card.deadline.slice(0, 10) < new Date().toISOString().slice(0, 10);

  return (
    <div className="card" style={{ borderLeft: `3px solid ${accent}`, padding: 10, marginBottom: 8 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{card.name}</div>
      <div className="row" style={{ gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
        <span className="chip" style={{ fontSize: 11 }}>{TASK_STATE_LABEL[card.state] ?? card.state}</span>
        {card.deadline ? (
          <span className="muted" style={{ fontSize: 11, color: overdue ? "var(--bad, #B23B3B)" : undefined }}>
            ⏰ {card.deadline.slice(0, 10)}
          </span>
        ) : null}
        {card.firmata ? <span className="chip" style={{ fontSize: 11 }}>✓ firmata</span> : null}
      </div>

      {column.kind === "pool" ? (
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          <button className="btn-mini" disabled={busy} onClick={() => run(() => claimTask(card.id))}>
            {busy ? "…" : "Prendi io"}
          </button>
          <select
            className="btn-mini"
            disabled={busy}
            defaultValue=""
            onChange={(e) => { const v = Number(e.target.value); if (v) run(() => assignTask(card.id, v)); }}
            style={{ maxWidth: 140 }}
          >
            <option value="" disabled>Assegna a…</option>
            {assignees.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
      ) : (
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          {next === "checkin" ? (
            <button className="btn-mini" disabled={busy} onClick={() => run(() => taskCheckin(card.id))}>
              {busy ? "…" : "Check-in"}
            </button>
          ) : null}
          {next === "checkout" ? (
            <button className="btn-mini" disabled={busy} onClick={() => run(() => taskCheckout(card.id))}>
              {busy ? "…" : "Check-out"}
            </button>
          ) : null}
          {next === "sign" ? (
            <button className="btn-mini" disabled={busy} onClick={() => run(() => taskSign(card.id))}>
              {busy ? "…" : "Firma e chiudi"}
            </button>
          ) : null}
          <button className="btn-mini" disabled={busy} onClick={() => run(() => assignTask(card.id, null))}>
            → Pool
          </button>
        </div>
      )}

      {msg ? <div style={{ color: "var(--bad, #B23B3B)", fontSize: 12, marginTop: 6 }}>{msg}</div> : null}
    </div>
  );
}
