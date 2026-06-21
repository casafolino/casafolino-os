"use client";
// Kanban pipeline (Brief 6): colonne = stage non terminali. Drag tra colonne → console_set_lead_stage
// (ottimistico: muovo subito, rollback visivo se il server fallisce). Menu card → Vinta/Persa/Standby
// (stage terminali → la card esce dalla board). Card → /lead/[id]. Lancio campionatura conservato.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getBoard, setLeadStage, type Board, type BoardCard, rottingColor } from "@/lib/pipeline";
import { moneyCompact } from "@/components/Honest";
import { CampionaturaButton } from "@/components/CampionaturaButton";

export function KanbanBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [drag, setDrag] = useState<{ leadId: number; fromStage: number } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const b = await getBoard();
      if (b?.columns) setBoard(b); else setErr((b as { message?: string }).message ?? "errore");
    } catch (e) { setErr((e as Error).message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  // sposta una card tra colonne nello stato locale (ottimistico)
  function moveLocal(prev: Board, leadId: number, fromStage: number, toStage: number): Board {
    if (fromStage === toStage) return prev;
    let card: BoardCard | undefined;
    const columns = prev.columns.map((c) => {
      if (c.stageId === fromStage) {
        card = c.cards.find((x) => x.id === leadId);
        return { ...c, cards: c.cards.filter((x) => x.id !== leadId), count: c.count - (card ? 1 : 0) };
      }
      return c;
    });
    if (!card) return prev;
    return {
      ...prev,
      columns: columns.map((c) => (c.stageId === toStage ? { ...c, cards: [card!, ...c.cards], count: c.count + 1 } : c)),
    };
  }
  function removeLocal(prev: Board, leadId: number): Board {
    return { ...prev, columns: prev.columns.map((c) => ({ ...c, cards: c.cards.filter((x) => x.id !== leadId), count: c.cards.some((x) => x.id === leadId) ? c.count - 1 : c.count })) };
  }

  async function onDrop(toStage: number) {
    if (!drag || !board) return;
    const { leadId, fromStage } = drag;
    setDrag(null);
    if (fromStage === toStage) return;
    const snapshot = board;
    setBoard(moveLocal(board, leadId, fromStage, toStage)); // ottimistico
    try {
      const r = await setLeadStage(leadId, toStage);
      if (!r.ok) { setBoard(snapshot); setToast(r.message ?? "spostamento fallito"); } // rollback
    } catch (e) { setBoard(snapshot); setToast((e as Error).message); }
  }

  async function markTerminal(leadId: number, stageId: number, label: string) {
    if (!board) return;
    const snapshot = board;
    setBoard(removeLocal(board, leadId)); // ottimistico: esce dalla board
    try {
      const r = await setLeadStage(leadId, stageId);
      if (!r.ok) { setBoard(snapshot); setToast(r.message ?? "errore"); }
      else setToast(`Segnato ${label}`);
    } catch (e) { setBoard(snapshot); setToast((e as Error).message); }
  }

  if (err) return <div className="card" style={{ padding: 16, color: "var(--danger)" }}>Errore: {err}</div>;
  if (!board) return <div className="muted" style={{ padding: 16 }}>Carico pipeline…</div>;

  return (
    <>
      {toast ? <div className="chip" style={{ background: "var(--warn-t)", color: "var(--warn)", marginBottom: 8 }} onClick={() => setToast(null)}>{toast} ✕</div> : null}
      <div style={{ display: "flex", gap: 11, alignItems: "flex-start", overflowX: "auto" }}>
        {board.columns.map((col) => (
          <div key={col.stageId} className="grow" style={{ minWidth: 220 }}
            onDragOver={(e) => e.preventDefault()} onDrop={() => onDrop(col.stageId)}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 9 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>{col.name}</span>
              <span className="muted" style={{ fontSize: 11 }}>{col.count}</span>
            </div>
            {col.cards.length === 0 ? (
              <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>—</div>
            ) : col.cards.map((c) => (
              <KanbanCard key={c.id} card={c} fromStage={col.stageId}
                terminals={board.terminalStages}
                onDragStart={() => setDrag({ leadId: c.id, fromStage: col.stageId })}
                onMarkTerminal={markTerminal} />
            ))}
          </div>
        ))}
      </div>
    </>
  );
}

function KanbanCard({ card, fromStage, terminals, onDragStart, onMarkTerminal }: {
  card: BoardCard; fromStage: number;
  terminals: Board["terminalStages"];
  onDragStart: () => void;
  onMarkTerminal: (leadId: number, stageId: number, label: string) => void;
}) {
  const [menu, setMenu] = useState(false);
  const rot = card.rottingState ? rottingColor[card.rottingState] : null;
  const stuck = card.daysInStage != null && card.daysInStage >= 7;
  void fromStage;
  return (
    <div className="card" draggable onDragStart={onDragStart}
      style={{ borderLeft: `3px solid ${rot ?? "var(--line)"}`, padding: 10, marginBottom: 8, cursor: "grab", position: "relative" }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <Link href={`/lead/${card.id}`} style={{ fontWeight: 600, fontSize: 13, color: "var(--ink)" }}>{card.name}</Link>
        <span onClick={() => setMenu((m) => !m)} style={{ cursor: "pointer", padding: "0 4px", color: "var(--muted)" }}>⋯</span>
      </div>
      {card.company ? <div className="muted" style={{ fontSize: 11 }}>{card.company}</div> : null}
      <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 12 }}>{card.value != null ? moneyCompact(card.value) : "—"}</span>
        {card.score != null ? <span className="chip" style={{ fontSize: 10 }}>{card.score}</span> : null}
      </div>
      <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
        {card.daysInStage != null ? (
          <span className="chip" style={{ fontSize: 10, background: stuck ? "var(--danger-t)" : "var(--panel-2)", color: stuck ? "var(--danger)" : "var(--muted)" }}>
            {stuck ? `ferma ${card.daysInStage}g` : `${card.daysInStage}g`}
          </span>
        ) : <span />}
        <span className="muted" style={{ fontSize: 10 }}>{card.owner}</span>
      </div>
      <div style={{ marginTop: 6 }}>
        <CampionaturaButton partnerId={card.partnerId} leadId={card.id} small label="+ Campionatura" />
      </div>
      {menu ? (
        <div className="card" style={{ position: "absolute", right: 8, top: 28, zIndex: 20, padding: 4, boxShadow: "0 4px 16px rgba(0,0,0,0.15)" }}>
          {terminals.map((t) => (
            <div key={t.stageId} className="hover-row" style={{ padding: "6px 10px", cursor: "pointer", fontSize: 12, whiteSpace: "nowrap" }}
              onClick={() => { setMenu(false); onMarkTerminal(card.id, t.stageId, t.name); }}>
              Segna {t.name}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
