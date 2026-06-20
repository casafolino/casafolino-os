"use client";
// Inbox 3-pane interattivo + triage bulk (tieni/scarta/cestina) via gateway.
// Multi-select (riga / gruppo / mittente / tutto), barra azioni, conferma cestina, undo.
// Nessun unlink: 'cestina' = stato trash soft, recuperabile dal Cestino.
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Icon } from "./Icons";
import { PartnerMailThread } from "./PartnerMailThread";
import { AiDraftButton } from "./AiDraftButton";
import { CreateLeadButton } from "./CreateLeadButton";
import { LinkLeadButton } from "./LinkLeadButton";
import { money, moneyCompact, dateLabel } from "./Honest";
import { operatorColor } from "@/lib/theme";
import { BP } from "@/lib/basePath";
import type { InboxItem, PartnerBundle, Tone } from "@/lib/types";

function toneStyle(t: Tone): React.CSSProperties {
  switch (t) {
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}
function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

type Snack = { text: string; prev: Record<number, string> } | null;

async function triageCall(ids: number[], state: string): Promise<{ ok: boolean; message?: string }> {
  const res = await fetch(`${BP}/api/console/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids, state }),
  });
  return res.json().catch(() => ({ ok: false, message: "errore rete" }));
}

export function InboxClient({
  items,
  bundles,
  initialSelectedId,
  view = "inbox",
}: {
  items: InboxItem[];
  bundles: Record<number, PartnerBundle>;
  initialSelectedId: number;
  view?: "inbox" | "trash";
}) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState(initialSelectedId);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [snack, setSnack] = useState<Snack>(null);
  const [confirmTrash, setConfirmTrash] = useState(false);

  const item = items.find((i) => i.id === selectedId) ?? items[0];
  const bundle = item?.partnerId ? bundles[item.partnerId] : null;
  const m = item?.message;

  // raggruppa per azienda (org) per "seleziona gruppo".
  const groups = useMemo(() => {
    const map = new Map<string, InboxItem[]>();
    for (const it of items) {
      const k = it.org || it.senderEmail || "—";
      const arr = map.get(k);
      if (arr) arr.push(it); else map.set(k, [it]);
    }
    return [...map.entries()];
  }, [items]);

  const allChecked = items.length > 0 && checked.size === items.length;
  function toggle(id: number) {
    setChecked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  }
  function setMany(ids: number[], on: boolean) {
    setChecked((s) => { const n = new Set(s); ids.forEach((i) => (on ? n.add(i) : n.delete(i))); return n; });
  }
  function selectAll() { setChecked(allChecked ? new Set() : new Set(items.map((i) => i.id))); }
  function selectSender(email: string) { setMany(items.filter((i) => i.senderEmail === email).map((i) => i.id), true); }

  async function applyBulk(state: string) {
    const ids = [...checked];
    if (!ids.length) return;
    const prev: Record<number, string> = {};
    items.forEach((i) => { if (checked.has(i.id)) prev[i.id] = i.state; });
    setBusy(true);
    const r = await triageCall(ids, state);
    setBusy(false);
    setConfirmTrash(false);
    if (!r.ok) { setSnack({ text: `Errore: ${r.message ?? "triage fallito"}`, prev: {} }); return; }
    const verb = state === "keep" ? "tenuti" : state === "discard" ? "scartati" : state === "trash" ? "cestinati" : "ripristinati";
    setChecked(new Set());
    setSnack({ text: `${ids.length} ${verb}`, prev });
    router.refresh();
  }

  async function undo() {
    if (!snack || !Object.keys(snack.prev).length) { setSnack(null); return; }
    // ripristina ogni messaggio al suo stato precedente (raggruppa per stato).
    const byState = new Map<string, number[]>();
    for (const [id, st] of Object.entries(snack.prev)) {
      const arr = byState.get(st);
      if (arr) arr.push(Number(id)); else byState.set(st, [Number(id)]);
    }
    setBusy(true);
    for (const [st, ids] of byState) await triageCall(ids, st);
    setBusy(false);
    setSnack(null);
    router.refresh();
  }

  return (
    <>
      {/* Pane 2: lista + toolbar selezione */}
      <div style={{ width: 250, flexShrink: 0, borderRight: "1px solid var(--line)", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "9px 12px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 8 }}>
          <strong style={{ flex: 1 }}>{view === "trash" ? "Cestino" : "Inbox"}</strong>
          <Link href={view === "trash" ? "/inbox" : "/inbox?view=trash"} className="muted" style={{ fontSize: 11 }}>
            {view === "trash" ? "← Inbox" : "Cestino"}
          </Link>
        </div>
        <label style={{ padding: "7px 12px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 7, fontSize: 12, cursor: "pointer" }}>
          <input type="checkbox" checked={allChecked} onChange={selectAll} />
          Seleziona tutto ({items.length})
        </label>

        <div style={{ overflowY: "auto", flex: 1 }}>
          {groups.map(([org, its]) => {
            const groupIds = its.map((i) => i.id);
            const groupAll = its.every((i) => checked.has(i.id));
            return (
              <div key={org}>
                <div style={{ padding: "5px 12px", background: "var(--panel-2)", display: "flex", alignItems: "center", gap: 6, fontSize: 10, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--muted)" }}>
                  <input type="checkbox" checked={groupAll} onChange={() => setMany(groupIds, !groupAll)} title="Seleziona gruppo" />
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{org}</span>
                  <span>{its.length}</span>
                </div>
                {its.map((it) => {
                  const sel = it.id === selectedId;
                  const ck = checked.has(it.id);
                  return (
                    <div key={it.id} style={{
                      padding: "9px 12px", display: "flex", gap: 8,
                      borderLeft: `3px solid ${sel ? "var(--accent)" : "transparent"}`,
                      background: ck ? "var(--accent-t)" : sel ? "var(--panel-2)" : "transparent",
                    }}>
                      <input type="checkbox" checked={ck} onChange={() => toggle(it.id)} style={{ marginTop: 3 }} />
                      <div style={{ flex: 1, minWidth: 0, cursor: "pointer" }} onClick={() => setSelectedId(it.id)}>
                        <div className="row" style={{ gap: 6 }}>
                          <span className="opdot" style={{ background: operatorColor[it.operator] }} />
                          <span style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.name}</span>
                        </div>
                        <div className="muted" style={{ fontSize: 11, margin: "2px 0 4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {it.accountName ? <span title="casella">{it.accountName} · </span> : null}{it.message.subject}
                        </div>
                        <div className="row" style={{ gap: 5 }}>
                          {it.badgeLabel ? <span className="chip" style={toneStyle(it.badgeTone)}>{it.badgeLabel}</span> : null}
                          <button onClick={(e) => { e.stopPropagation(); selectSender(it.senderEmail); }} className="muted" style={{ fontSize: 10, border: "none", background: "none", cursor: "pointer", textDecoration: "underline" }} title="Seleziona tutti da questo mittente">da mittente</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
          {items.length === 0 ? <div className="muted" style={{ padding: 16, fontSize: 12 }}>{view === "trash" ? "Cestino vuoto." : "Inbox vuota."}</div> : null}
        </div>

        {/* barra azioni bulk */}
        {checked.size > 0 ? (
          <div style={{ borderTop: "1px solid var(--line)", padding: "8px 10px", display: "flex", flexWrap: "wrap", gap: 6, background: "var(--paper)" }}>
            <span style={{ fontSize: 12, fontWeight: 600, width: "100%" }}>{checked.size} selezionati</span>
            {view === "trash" ? (
              <button disabled={busy} onClick={() => applyBulk("review")} className="btn">↩ Ripristina</button>
            ) : (
              <>
                <button disabled={busy} onClick={() => applyBulk("keep")} className="btn" style={{ background: "var(--ok-t)", color: "var(--ok)" }}>★ Tieni</button>
                <button disabled={busy} onClick={() => applyBulk("discard")} className="btn">✕ Scarta</button>
                <button disabled={busy} onClick={() => setConfirmTrash(true)} className="btn" style={{ background: "var(--danger-t)", color: "var(--danger)" }}>🗑 Cestina</button>
              </>
            )}
            <button disabled={busy} onClick={() => setChecked(new Set())} className="btn">Deseleziona</button>
          </div>
        ) : null}
      </div>

      {/* Pane 3: corpo + contesto */}
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {!item || !m ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest"><span>{view === "trash" ? "Cestino vuoto." : "Nessuna mail in coda: la inbox è vuota."}</span></div>
          </div>
        ) : (
        <div className="card" style={{ padding: "14px 16px" }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.subject || "(senza oggetto)"}</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 11 }}>
            <span style={{ color: "var(--ink)", fontWeight: 600 }}>{m.senderName}</span> · {m.senderEmail} · {m.timeLabel}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 13 }}>{m.body}</div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <span className="btn pri"><Icon name="reply" size={14} /> Rispondi · F8</span>
            <AiDraftButton subject={m.subject} body={m.body} partnerName={m.senderName} to={m.senderEmail} />
            <LinkLeadButton messageId={item.id} leadId={bundle?.leads[0]?.id ?? null} leadName={bundle?.leads[0]?.name} />
          </div>
        </div>
        )}

        {item && bundle ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--ok-t)", color: "var(--ok)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, flexShrink: 0 }}>{initials(bundle.partner.name)}</div>
              <div className="grow">
                <div style={{ fontWeight: 600 }}>
                  <Link href={`/partner/${bundle.partner.id}`} style={{ color: "var(--accent)" }}>{bundle.partner.name} →</Link>
                  {bundle.partner.role || bundle.partner.country ? <span className="chip" style={{ marginLeft: 4 }}>{[bundle.partner.role, bundle.partner.country].filter(Boolean).join(" · ")}</span> : null}
                </div>
                <div className="muted" style={{ fontSize: 11 }}>
                  <Icon name="check" size={13} color="var(--ok)" /> riconosciuto dal mittente · match {item.resolutionMatch === "domain" ? "dominio " : item.resolutionMatch === "exact" ? "esatto " : ""}
                  <span style={{ fontFamily: "var(--mono)" }}>{bundle.partner.domain ?? bundle.partner.email}</span>
                </div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              <Cell label="Lead" value={bundle.leads[0] ? `${bundle.leads[0].stage ?? "lead"} · score ${bundle.leads[0].score ?? "n/d"}` : null} empty="Nessun lead" accent={false} />
              <Cell label="Dossier" value={bundle.dossiers[0] ? `${bundle.dossiers[0].name} · ${bundle.dossiers[0].status ?? ""}` : null} empty="Nessun dossier" accent href={bundle.dossiers[0] ? "/dossier" : undefined} />
              <Cell label="Ultimo ordine" value={lastOrder(bundle)} empty="Nessun ordine" accent={false} />
              <Cell label="Fatturato" value={bundle.revenue.total > 0 ? moneyCompact(bundle.revenue.total) : null} empty="Nessun fatturato" accent={false} />
            </div>
            {bundle.signals.nbaText ? (
              <div className="row" style={{ gap: 8, background: "var(--warn-t)", padding: "8px 11px", borderRadius: "var(--r-md)", marginBottom: 12 }}>
                <Icon name="alert" size={16} color="var(--warn)" />
                <span className="grow" style={{ fontSize: 12, color: "#6B4A12" }}><b>Prossima azione:</b> {bundle.signals.nbaText}</span>
              </div>
            ) : null}
            <PartnerMailThread messages={bundle.mailThread} title="Mail con questo partner (qui, nel lead, nel dossier)" limit={5} />
          </div>
        ) : item && m ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest">
              <span>Mittente non riconosciuto: nessun partner collegato.</span>
              <CreateLeadButton name={`Nuovo contatto · ${m.senderName || m.senderEmail}`} emailFrom={m.senderEmail} />
            </div>
            <div style={{ marginTop: 10 }}><PartnerMailThread messages={[]} title="Mail con questo partner" /></div>
          </div>
        ) : null}
      </main>

      {/* conferma cestina (bulk irreversibile-look → conferma obbligatoria) */}
      {confirmTrash ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={() => setConfirmTrash(false)}>
          <div className="card" style={{ padding: 22, width: 320 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Cestina {checked.size} messaggi?</div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>Vanno nel Cestino (recuperabili). Nessuna cancellazione fisica.</div>
            <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
              <button className="btn" onClick={() => setConfirmTrash(false)}>Annulla</button>
              <button className="btn" disabled={busy} style={{ background: "var(--danger-t)", color: "var(--danger)" }} onClick={() => applyBulk("trash")}>🗑 Cestina</button>
            </div>
          </div>
        </div>
      ) : null}

      {/* snackbar undo */}
      {snack ? (
        <div style={{ position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)", background: "var(--ink)", color: "#fff", padding: "10px 14px", borderRadius: 8, display: "flex", gap: 14, alignItems: "center", zIndex: 60, boxShadow: "0 4px 16px rgba(0,0,0,.25)" }}>
          <span style={{ fontSize: 13 }}>{snack.text}</span>
          {Object.keys(snack.prev).length ? (
            <button onClick={undo} disabled={busy} style={{ background: "none", border: "none", color: "#9ec46a", fontWeight: 700, cursor: "pointer" }}>Annulla</button>
          ) : null}
          <button onClick={() => setSnack(null)} style={{ background: "none", border: "none", color: "#aaa", cursor: "pointer" }}>✕</button>
        </div>
      ) : null}
    </>
  );
}

function Cell({ label, value, empty, accent, href }: { label: string; value: string | null; empty: string; accent: boolean; href?: string }) {
  const text = (
    <div style={{ fontWeight: 600, fontSize: 13, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}{href ? " →" : ""}</div>
  );
  return (
    <div>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      {value ? (href ? <Link href={href}>{text}</Link> : text) : <div style={{ fontSize: 12, color: "var(--muted)" }}>{empty}</div>}
    </div>
  );
}
function lastOrder(bundle: PartnerBundle): string | null {
  const real = bundle.orders.filter((o) => !o.isSample);
  if (real.length === 0) return null;
  return `${dateLabel(real[0].dateOrder)} · ${money(real[0].amountTotal, bundle.revenue.currency)}`;
}
