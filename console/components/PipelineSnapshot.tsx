"use client";
// Fase 2 WI-D — pipeline snapshot azionabile. Click su uno stage → deal di quello stage →
// avanzamento stage direttamente (via crm.lead.console_set_lead_stage gated). SWR-like fetch client.
import { useEffect, useState, useCallback } from "react";
import { getBoard, setLeadStage, activityColor, type Board, type BoardColumn } from "@/lib/pipeline";
import { BP } from "@/lib/basePath";

function money(n: number | null): string {
  if (!n) return "—";
  return n >= 1000 ? `€${(n / 1000).toFixed(1)}k` : `€${n.toFixed(0)}`;
}

export function PipelineSnapshot() {
  const [board, setBoard] = useState<Board | null>(null);
  const [openStage, setOpenStage] = useState<number | null>(null);
  const [busyLead, setBusyLead] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const b = await getBoard();
      setBoard(b);
      if (b.message) setErr(b.message);
    } catch (e) { setErr((e as Error).message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function advance(leadId: number, stageId: number) {
    setBusyLead(leadId); setErr(null);
    try {
      const r = await setLeadStage(leadId, stageId);
      if (!r.ok && r.message) setErr(r.message);
      await load();
    } catch (e) { setErr((e as Error).message); }
    finally { setBusyLead(null); }
  }

  if (!board) return <div className="card" style={{ padding: 14 }}><span className="muted">Carico pipeline…</span></div>;
  const cols = board.columns;
  const totalLeads = cols.reduce((s, c) => s + c.count, 0);

  return (
    <div className="card" style={{ padding: 14, marginBottom: 18 }}>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <h3 className="sec-title" style={{ margin: 0 }}>Pipeline snapshot</h3>
        <span className="muted" style={{ fontSize: 12 }}>{totalLeads} opportunità · clicca uno stage</span>
      </div>

      {/* stage cliccabili */}
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        {cols.map((c) => {
          const val = c.cards.reduce((s, k) => s + (k.value ?? 0), 0);
          const active = openStage === c.stageId;
          return (
            <button key={c.stageId} className="card" onClick={() => setOpenStage(active ? null : c.stageId)}
              style={{ padding: "8px 12px", cursor: "pointer", borderColor: active ? "var(--accent)" : "var(--line)",
                background: active ? "var(--accent-t)" : "var(--panel)", textAlign: "left" }}>
              <div style={{ fontSize: 12, fontWeight: 700 }}>{c.name}</div>
              <div className="muted" style={{ fontSize: 11 }}>{c.count} deal · {money(val)}</div>
            </button>
          );
        })}
      </div>

      {err ? <div style={{ marginTop: 8, fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}

      {openStage != null ? <StageDeals col={cols.find((c) => c.stageId === openStage)!} cols={cols}
        terminalStages={board.terminalStages} busyLead={busyLead} onAdvance={advance} /> : null}
    </div>
  );
}

function StageDeals({ col, cols, terminalStages, busyLead, onAdvance }: {
  col: BoardColumn; cols: BoardColumn[]; terminalStages: Board["terminalStages"];
  busyLead: number | null; onAdvance: (leadId: number, stageId: number) => void;
}) {
  const idx = cols.findIndex((c) => c.stageId === col.stageId);
  const prev = idx > 0 ? cols[idx - 1] : null;
  const next = idx < cols.length - 1 ? cols[idx + 1] : null;
  const won = terminalStages.find((t) => t.isWon);

  if (col.cards.length === 0)
    return <div className="muted" style={{ marginTop: 10, fontSize: 12, padding: 8 }}>Nessun deal in «{col.name}».</div>;

  return (
    <div className="card" style={{ marginTop: 10, padding: 0, overflow: "hidden" }}>
      {col.cards.map((k, i) => (
        <div key={k.id} className="row" style={{ padding: "8px 12px", gap: 10, borderTop: i ? "1px solid var(--line)" : "none" }}>
          <span className="opdot" style={{ background: activityColor[k.activityState || "neutral"] }} />
          <a href={`${BP}/lead/${k.id}`} style={{ fontWeight: 600, minWidth: 150 }}>{k.name}</a>
          <span className="muted grow ell" style={{ fontSize: 12 }}>{k.company} · {k.owner}</span>
          <span className="muted" style={{ fontSize: 12 }}>{money(k.value)}</span>
          <div className="row" style={{ gap: 4 }}>
            {prev ? <button className="btn-mini" disabled={busyLead === k.id} title={`← ${prev.name}`} onClick={() => onAdvance(k.id, prev.stageId)}>‹</button> : null}
            {next ? <button className="btn-mini" disabled={busyLead === k.id} title={`→ ${next.name}`} onClick={() => onAdvance(k.id, next.stageId)}>›</button> : null}
            {won ? <button className="btn-mini" disabled={busyLead === k.id} title={`Vinta: ${won.name}`} onClick={() => onAdvance(k.id, won.stageId)}>✓</button> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
