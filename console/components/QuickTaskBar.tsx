"use client";
// Fase 2 — Quick-Task in linguaggio naturale. Scrivi un'istruzione, Groq la parsa, la card di
// conferma (editabile) è OBBLIGATORIA prima di ogni scrittura. Instrada a attività/campione/task.
import { useState } from "react";
import { parseQuicktask, commitQuicktask, type ParsedQuicktask, type ActionType } from "@/lib/quicktask";
import { universalSearch, type SearchItem } from "@/lib/pipeline";
import { searchProducts, type ProductHit } from "@/lib/campionatura";

const ACTIONS: { v: ActionType; label: string }[] = [
  { v: "catalogo", label: "Invia catalogo" },
  { v: "email", label: "Invia email" },
  { v: "follow-up", label: "Follow-up" },
  { v: "sollecito", label: "Sollecito" },
  { v: "campione", label: "Campione" },
  { v: "task", label: "Task operativo" },
];

function inputStyle(bad = false): React.CSSProperties {
  return { width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
    border: bad ? "1px solid var(--danger)" : "1px solid var(--line)",
    background: bad ? "var(--danger-t)" : "var(--paper)" };
}

type Target = { kind: "partner" | "lead"; id: number; label: string };

export function QuickTaskBar() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [parsed, setParsed] = useState<ParsedQuicktask | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  // campi editabili della card
  const [action, setAction] = useState<ActionType>("");
  const [summary, setSummary] = useState("");
  const [due, setDue] = useState("");
  const [target, setTarget] = useState<Target | null>(null);
  const [lines, setLines] = useState<{ productId: number; qty: number; name: string }[]>([]);

  async function onParse() {
    if (!text.trim()) return;
    setBusy(true); setErr(null); setDone(null);
    try {
      const r = await parseQuicktask(text.trim());
      if (r.message) { setErr(r.message); setParsed(null); }
      else {
        setParsed(r);
        setAction(r.actionType);
        setSummary(r.objectRef ? `${ACTIONS.find((a) => a.v === r.actionType)?.label ?? ""} — ${r.objectRef}`.trim() : "");
        setDue(r.dueDate);
        setTarget(null); setLines([]);
      }
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  async function onCommit() {
    if (!parsed) return;
    setBusy(true); setErr(null);
    try {
      const r = await commitQuicktask({
        action_type: action,
        assignee_user_id: parsed.assignee.resolved?.userId ?? null,
        assignee_employee_id: parsed.assignee.resolved?.employeeId ?? null,
        partner_id: target?.kind === "partner" ? target.id : null,
        lead_id: target?.kind === "lead" ? target.id : null,
        summary: summary || undefined,
        due_date: due || undefined,
        lines: lines.map((l) => ({ productId: l.productId, qty: l.qty })),
      });
      if (r.ok) {
        setDone(`Creato: ${r.kind}${r.id ? ` #${r.id}` : ""}`);
        setParsed(null); setText(""); setTarget(null); setLines([]);
      } else setErr(r.message || "Errore in scrittura.");
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  const isActivity = ["catalogo", "email", "follow-up", "sollecito"].includes(action);
  const needsTarget = isActivity || action === "campione";
  const needsLines = action === "campione";
  const canCommit = !!action && (!needsTarget || !!target) && (!needsLines || lines.length > 0) &&
    (action !== "task" || !!summary.trim());

  return (
    <div className="card" style={{ padding: 14, marginBottom: 18 }}>
      <div className="row" style={{ gap: 8 }}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !busy) onParse(); }}
          placeholder='Es. "Anna manda 1 campione di miele al laboratorio analisi"'
          style={inputStyle()}
          aria-label="Quick task"
        />
        <button className="btn-secondary" disabled={busy || !text.trim()} onClick={onParse}>
          {busy && !parsed ? "…" : "Interpreta"}
        </button>
      </div>
      {done ? <div style={{ marginTop: 8, fontSize: 12, color: "var(--ok)" }}>{done}</div> : null}
      {err ? <div style={{ marginTop: 8, fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}

      {parsed ? (
        <div style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 12, display: "grid", gap: 10 }}>
          {parsed.needsReview ? (
            <div style={{ fontSize: 12, color: "var(--warn)" }}>
              Istruzione ambigua — completa i campi evidenziati prima di confermare.
            </div>
          ) : null}

          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <span className="muted" style={{ width: 80, fontSize: 12 }}>Assegnato a</span>
            <div style={{ ...inputStyle(!parsed.assignee.resolved), flex: 1, padding: "7px 10px" }}>
              {parsed.assignee.resolved
                ? <strong>{parsed.assignee.resolved.name}</strong>
                : <span className="muted">non riconosciuto — fallback operatore corrente</span>}
            </div>
          </div>

          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <span className="muted" style={{ width: 80, fontSize: 12 }}>Azione</span>
            <select value={action} onChange={(e) => setAction(e.target.value as ActionType)} style={{ ...inputStyle(!action), flex: 1 }}>
              <option value="">— scegli —</option>
              {ACTIONS.map((a) => <option key={a.v} value={a.v}>{a.label}</option>)}
            </select>
          </div>

          {needsTarget ? <TargetPicker target={target} onPick={setTarget} /> : null}
          {needsLines ? <LinePicker lines={lines} onChange={setLines} /> : null}

          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <span className="muted" style={{ width: 80, fontSize: 12 }}>{action === "task" ? "Titolo" : "Oggetto"}</span>
            <input value={summary} onChange={(e) => setSummary(e.target.value)}
              style={inputStyle(action === "task" && !summary.trim())} placeholder="riepilogo" />
          </div>

          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <span className="muted" style={{ width: 80, fontSize: 12 }}>Scadenza</span>
            <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={{ ...inputStyle(), flex: "0 0 170px" }} />
          </div>

          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button className="btn-mini" onClick={() => setParsed(null)}>Annulla</button>
            <button className="btn-primary" disabled={busy || !canCommit} onClick={onCommit}>
              {busy ? "Scrivo…" : "Conferma e crea"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function TargetPicker({ target, onPick }: { target: Target | null; onPick: (t: Target | null) => void }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ kind: "partner" | "lead"; item: SearchItem }[]>([]);
  const [busy, setBusy] = useState(false);
  async function run() {
    if (!q.trim()) return;
    setBusy(true);
    try {
      const r = await universalSearch(q.trim());
      const out: { kind: "partner" | "lead"; item: SearchItem }[] = [];
      for (const g of r.groups) {
        if (g.type === "partner" || g.type === "lead")
          for (const it of g.items) out.push({ kind: g.type, item: it });
      }
      setHits(out.slice(0, 8));
    } finally { setBusy(false); }
  }
  if (target) {
    return (
      <div className="row" style={{ gap: 10, alignItems: "center" }}>
        <span className="muted" style={{ width: 80, fontSize: 12 }}>Destinatario</span>
        <div style={{ ...inputStyle(), flex: 1, padding: "7px 10px" }}>
          <strong>{target.label}</strong> <span className="muted">({target.kind})</span>
        </div>
        <button className="btn-mini" onClick={() => onPick(null)}>cambia</button>
      </div>
    );
  }
  return (
    <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
      <span className="muted" style={{ width: 80, fontSize: 12, paddingTop: 8 }}>Destinatario</span>
      <div style={{ flex: 1 }}>
        <div className="row" style={{ gap: 8 }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") run(); }}
            style={inputStyle(!target)} placeholder="cerca cliente o opportunità" />
          <button className="btn-mini" disabled={busy} onClick={run}>cerca</button>
        </div>
        {hits.length > 0 ? (
          <div className="card" style={{ marginTop: 6, padding: 0, overflow: "hidden" }}>
            {hits.map((h, i) => (
              <button key={i} className="row" style={{ width: "100%", padding: "7px 10px", textAlign: "left", borderBottom: "1px solid var(--line)", background: "transparent" }}
                onClick={() => { onPick({ kind: h.kind, id: h.item.id, label: h.item.title }); setHits([]); }}>
                <span style={{ fontWeight: 600 }}>{h.item.title}</span>
                <span className="muted grow ell" style={{ fontSize: 12 }}>{h.item.subtitle}</span>
                <span className="chip">{h.kind}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function LinePicker({ lines, onChange }: { lines: { productId: number; qty: number; name: string }[]; onChange: (l: { productId: number; qty: number; name: string }[]) => void }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<ProductHit[]>([]);
  async function run() {
    if (!q.trim()) return;
    setHits((await searchProducts(q.trim())).slice(0, 6));
  }
  return (
    <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
      <span className="muted" style={{ width: 80, fontSize: 12, paddingTop: 8 }}>Prodotti</span>
      <div style={{ flex: 1 }}>
        {lines.map((l, i) => (
          <div key={i} className="row" style={{ gap: 8, marginBottom: 4 }}>
            <span style={{ flex: 1, fontWeight: 600 }}>{l.name}</span>
            <input type="number" min={1} value={l.qty}
              onChange={(e) => onChange(lines.map((x, j) => j === i ? { ...x, qty: Number(e.target.value) } : x))}
              style={{ ...inputStyle(), width: 64 }} />
            <button className="btn-mini" onClick={() => onChange(lines.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        <div className="row" style={{ gap: 8 }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") run(); }}
            style={inputStyle(lines.length === 0)} placeholder="cerca prodotto" />
          <button className="btn-mini" onClick={run}>cerca</button>
        </div>
        {hits.length > 0 ? (
          <div className="card" style={{ marginTop: 6, padding: 0, overflow: "hidden" }}>
            {hits.map((p) => (
              <button key={p.id} className="row" style={{ width: "100%", padding: "7px 10px", textAlign: "left", borderBottom: "1px solid var(--line)", background: "transparent" }}
                onClick={() => { onChange([...lines, { productId: p.id, qty: 1, name: p.name }]); setHits([]); setQ(""); }}>
                <span style={{ fontWeight: 600 }}>{p.name}</span>
                <span className="muted grow ell" style={{ fontSize: 12 }}>{p.code}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
