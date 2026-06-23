"use client";
// Kanban pipeline (Brief 6 + restyle F2): colonne = stage non terminali. Drag tra colonne → console_set_lead_stage
// (ottimistico: muovo subito, rollback visivo se il server fallisce). Menu card → Vinta/Persa/Standby
// (stage terminali → la card esce dalla board). Card → /lead/[id]. Lancio campionatura conservato.
// F2: header colonna con conteggio + somma €; ordinamento valore/rotting/attività; card con DS atoms.
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getBoard, setLeadStage, type Board, type BoardCard } from "@/lib/pipeline";
import { moneyCompact } from "@/components/Honest";
import { Pill, Avatar, Toast } from "@/components/ds";
import { activityTone, type Tone } from "@/lib/tokens";
import { SavedViewBar, useSavedView, type SavedView } from "@/components/SavedViewBar";
import { CampionaturaButton } from "@/components/CampionaturaButton";

type SortKey = "value" | "rotting" | "activity";
const SORT_LABEL: Record<SortKey, string> = {
  value: "valore",
  rotting: "a rischio",
  activity: "inattività",
};
const ROT_RANK: Record<string, number> = { danger: 0, warning: 1, fresh: 2, neutral: 3 };

// F3 — viste salvate per la pipeline. "Campionature in corso" richiederebbe un flag campione
// sulla card (non presente in BoardCard → lettura gateway aggiuntiva): rinviata, non finta.
const VIEWS: SavedView[] = [
  { key: "all", label: "tutte" },
  { key: "mine", label: "le mie aperte" },
  { key: "rotting", label: "in marcire" },
  { key: "no-next", label: "senza prossima attività" },
];

function matchesView(card: BoardCard, view: string, me: string): boolean {
  if (view === "mine") return !!me && (card.owner || "").toLowerCase().includes(me.toLowerCase());
  if (view === "rotting") return card.activityState === "danger" || card.activityState === "warning";
  if (view === "no-next") return !card.activityState || card.activityState === "neutral" || card.daysInactive == null;
  return true;
}

function sortCards(cards: BoardCard[], key: SortKey): BoardCard[] {
  const arr = [...cards];
  if (key === "value") arr.sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  else if (key === "rotting")
    arr.sort((a, b) => (ROT_RANK[a.activityState ?? "neutral"] ?? 3) - (ROT_RANK[b.activityState ?? "neutral"] ?? 3));
  else if (key === "activity") arr.sort((a, b) => (b.daysInactive ?? -1) - (a.daysInactive ?? -1));
  return arr;
}

export function KanbanBoard({ me = "" }: { me?: string }) {
  const [board, setBoard] = useState<Board | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [drag, setDrag] = useState<{ leadId: number; fromStage: number } | null>(null);
  const [overStage, setOverStage] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; tone: Tone } | null>(null);
  const [sort, setSort] = useState<SortKey>("value");
  const [view, setView] = useSavedView("cf.console.pipeline.view", "all");

  const load = useCallback(async () => {
    try {
      const b = await getBoard();
      if (b?.columns) setBoard(b);
      else setErr((b as { message?: string }).message ?? "errore");
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

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
      columns: columns.map((c) =>
        c.stageId === toStage ? { ...c, cards: [card!, ...c.cards], count: c.count + 1 } : c
      ),
    };
  }
  function removeLocal(prev: Board, leadId: number): Board {
    return {
      ...prev,
      columns: prev.columns.map((c) => ({
        ...c,
        cards: c.cards.filter((x) => x.id !== leadId),
        count: c.cards.some((x) => x.id === leadId) ? c.count - 1 : c.count,
      })),
    };
  }

  async function onDrop(toStage: number) {
    setOverStage(null);
    if (!drag || !board) return;
    const { leadId, fromStage } = drag;
    setDrag(null);
    if (fromStage === toStage) return;
    const snapshot = board;
    setBoard(moveLocal(board, leadId, fromStage, toStage)); // ottimistico
    try {
      const r = await setLeadStage(leadId, toStage);
      if (!r.ok) {
        setBoard(snapshot);
        setToast({ msg: r.message ?? "spostamento fallito", tone: "danger" });
      }
    } catch (e) {
      setBoard(snapshot);
      setToast({ msg: (e as Error).message, tone: "danger" });
    }
  }

  async function markTerminal(leadId: number, stageId: number, label: string) {
    if (!board) return;
    const snapshot = board;
    setBoard(removeLocal(board, leadId)); // ottimistico: esce dalla board
    try {
      const r = await setLeadStage(leadId, stageId);
      if (!r.ok) {
        setBoard(snapshot);
        setToast({ msg: r.message ?? "errore", tone: "danger" });
      } else setToast({ msg: `Segnato ${label.toLowerCase()}`, tone: "success" });
    } catch (e) {
      setBoard(snapshot);
      setToast({ msg: (e as Error).message, tone: "danger" });
    }
  }

  const columns = useMemo(() => {
    if (!board) return [];
    return board.columns.map((c) => {
      const filtered = c.cards.filter((x) => matchesView(x, view, me));
      return {
        ...c,
        cards: sortCards(filtered, sort),
        count: filtered.length,
        sum: filtered.reduce((a, x) => a + (x.value ?? 0), 0),
      };
    });
  }, [board, sort, view, me]);

  if (err)
    return (
      <div className="card" style={{ padding: 16, color: "var(--danger)" }}>
        Errore: {err}
      </div>
    );
  if (!board) return <div className="muted" style={{ padding: 16 }}>Carico pipeline…</div>;

  return (
    <>
      {/* viste salvate (persistite) */}
      <div className="row" style={{ gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
        <span className="muted" style={{ fontSize: 12 }}>Vista</span>
        <SavedViewBar views={VIEWS} active={view} onChange={setView} />
      </div>

      {/* barra ordinamento */}
      <div className="row" style={{ gap: 6, marginBottom: 4 }}>
        <span className="muted" style={{ fontSize: 12 }}>Ordina per</span>
        {(Object.keys(SORT_LABEL) as SortKey[]).map((k) => (
          <button
            key={k}
            className="btn-mini"
            onClick={() => setSort(k)}
            style={
              sort === k
                ? { background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" }
                : undefined
            }
          >
            {SORT_LABEL[k]}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 11, alignItems: "flex-start", overflowX: "auto" }}>
        {columns.map((col) => (
          <div
            key={col.stageId}
            className="grow"
            style={{ minWidth: 224 }}
            onDragOver={(e) => {
              e.preventDefault();
              if (overStage !== col.stageId) setOverStage(col.stageId);
            }}
            onDrop={() => onDrop(col.stageId)}
          >
            <div
              style={{
                background: overStage === col.stageId ? "var(--accent-t)" : "transparent",
                borderRadius: "var(--r-md)",
                padding: 4,
                transition: "background 120ms",
              }}
            >
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 9, padding: "0 4px" }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{col.name}</span>
                <span className="row" style={{ gap: 6 }}>
                  <span className="muted" style={{ fontSize: 11 }}>{col.count}</span>
                  {col.sum > 0 ? <Pill tone="neutral" style={{ fontSize: 10 }}>{moneyCompact(col.sum)}</Pill> : null}
                </span>
              </div>
              {col.cards.length === 0 ? (
                <div className="empty-honest" style={{ fontSize: 12 }}>
                  <span>Nessuna trattativa in questa fase.</span>
                </div>
              ) : (
                col.cards.map((c) => (
                  <KanbanCard
                    key={c.id}
                    card={c}
                    terminals={board.terminalStages}
                    onDragStart={() => setDrag({ leadId: c.id, fromStage: col.stageId })}
                    onMarkTerminal={markTerminal}
                  />
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {toast ? <Toast message={toast.msg} tone={toast.tone} onDismiss={() => setToast(null)} /> : null}
    </>
  );
}

function KanbanCard({
  card,
  terminals,
  onDragStart,
  onMarkTerminal,
}: {
  card: BoardCard;
  terminals: Board["terminalStages"];
  onDragStart: () => void;
  onMarkTerminal: (leadId: number, stageId: number, label: string) => void;
}) {
  const [menu, setMenu] = useState(false);
  // Brief 20 B — rotting da attività reale; neutral = nessuna attività, MAI rosso falso.
  const state = card.activityState || "neutral";
  const tone = activityTone[state] ?? "neutral";
  const edge =
    tone === "danger" ? "var(--danger)" : tone === "warning" ? "var(--warn)" : tone === "success" ? "var(--ok)" : "var(--line)";

  return (
    <div
      className="card"
      draggable
      onDragStart={onDragStart}
      style={{ borderLeft: `3px solid ${edge}`, padding: 10, marginBottom: 8, cursor: "grab", position: "relative" }}
    >
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <Link href={`/lead/${card.id}`} style={{ fontWeight: 600, fontSize: 13, color: "var(--ink)" }}>
          {card.name}
        </Link>
        <span
          onClick={() => setMenu((m) => !m)}
          style={{ cursor: "pointer", padding: "0 4px", color: "var(--muted)" }}
          title="Segna stato finale"
        >
          ⋯
        </span>
      </div>
      {card.company ? <div className="muted" style={{ fontSize: 11 }}>{card.company}</div> : null}

      <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 12 }}>{card.value != null ? moneyCompact(card.value) : "valore non stimato"}</span>
        {card.score != null ? <Pill tone="info" style={{ fontSize: 10 }}>{card.score}</Pill> : null}
      </div>

      <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
        {card.daysInactive != null ? (
          <Pill tone={tone} style={{ fontSize: 10 }}>
            {tone === "danger" ? `ferma ${card.daysInactive}g` : `${card.daysInactive}g`}
          </Pill>
        ) : (
          <Pill tone="neutral" style={{ fontSize: 10 }}>nessuna attività</Pill>
        )}
        <Avatar name={card.owner} size={20} title={card.owner} />
      </div>

      <div style={{ marginTop: 6 }}>
        <CampionaturaButton partnerId={card.partnerId} leadId={card.id} small label="+ Campionatura" />
      </div>

      {menu ? (
        <div
          className="card"
          style={{ position: "absolute", right: 8, top: 28, zIndex: 20, padding: 4, boxShadow: "0 4px 16px rgba(0,0,0,0.15)" }}
        >
          {terminals.map((tt) => (
            <div
              key={tt.stageId}
              className="hover-row"
              style={{ padding: "6px 10px", cursor: "pointer", fontSize: 12, whiteSpace: "nowrap" }}
              onClick={() => {
                setMenu(false);
                onMarkTerminal(card.id, tt.stageId, tt.name);
              }}
            >
              Segna {tt.name.toLowerCase()}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
