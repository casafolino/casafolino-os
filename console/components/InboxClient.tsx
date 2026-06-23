"use client";
// Inbox 3-pane: lista per DATA/CASELLA + corpo completo. Due barre azioni STICKY in cima
// al pannello: Bar B (fissa, triage+selezione, target = selezione o mail aperta) e Bar A
// (contestuale, azioni della mail aperta). Scorciatoie da tastiera fuori dagli input.
// Tutto via gateway (console_triage / console_mark_read / reply / send): mai unlink/write raw.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Icon } from "./Icons";
import { PartnerMailThread } from "./PartnerMailThread";
import { AiDraftButton } from "./AiDraftButton";
import { CreateLeadButton } from "./CreateLeadButton";
import { LinkLeadButton } from "./LinkLeadButton";
import { Composer, type ComposerTarget, type ComposerMode, type Account } from "./Composer";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";
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
// Etichetta/tono dello stato triage per riga (così nei risultati sai dov'è la mail).
function stateChip(state: string): { label: string; tone: Tone } {
  switch (state) {
    case "keep": case "auto_keep": return { label: "Tenuta", tone: "ok" };
    case "discard": case "auto_discard": return { label: "Scartata", tone: "neutral" };
    case "trash": return { label: "Cestino", tone: "danger" };
    default: return { label: "Coda", tone: "warn" };
  }
}

type Snack = { text: string; prev: Record<number, string> } | null;
type GroupMode = "date" | "casella" | "mittente";
type GroupRec = { key: string; label: string; items: InboxItem[]; lastDate: string };
export type InboxView = "queue" | "all" | "keep" | "discard" | "trash";

// UNA sola vista nel flusso: Inbox = solo non-gestite (new/review). Tenute/Scartate/Cestino
// solo dal menu "Altro" (mai nel flusso primario).
const PRIMARY_TABS: { key: InboxView; label: string }[] = [
  { key: "queue", label: "Inbox" },
];
const BUCKET_TABS: { key: InboxView; label: string }[] = [
  { key: "keep", label: "Tenute" },
  { key: "discard", label: "Scartate" },
  { key: "trash", label: "Cestino" },
];

async function postJson(path: string, body: unknown): Promise<{ ok: boolean; message?: string; count?: number }> {
  const res = await fetch(`${BP}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.json().catch(() => ({ ok: false, message: "errore rete" }));
}

// Dropdown overflow minimale.
function More({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: "relative" }}>
      <button className="btn" onClick={() => setOpen((o) => !o)} onBlur={() => setTimeout(() => setOpen(false), 150)} title="Altro">⋯</button>
      {open ? (
        <div style={{ position: "absolute", top: "100%", right: 0, marginTop: 4, background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 8, boxShadow: "0 6px 18px rgba(0,0,0,.12)", padding: 4, zIndex: 20, minWidth: 170, display: "flex", flexDirection: "column", gap: 2 }}>
          {children}
        </div>
      ) : null}
    </div>
  );
}

export type SearchState = { q: string; sender: string; partner: number | null; active: boolean };

type SenderTarget = { partnerId?: number; senderEmail?: string; label: string; count: number };

export function InboxClient({
  items, bundles, initialSelectedId, view = "queue", scopeAll = false, queueCount = 0,
  search = { q: "", sender: "", partner: null, active: false }, senderCounts = {}, accounts = [], library = [], templates = [],
}: {
  items: InboxItem[];
  bundles: Record<number, PartnerBundle>;
  initialSelectedId: number;
  view?: InboxView;
  scopeAll?: boolean;
  queueCount?: number;
  search?: SearchState;
  senderCounts?: Record<string, number>;
  accounts?: Account[];
  library?: LibraryItem[];
  templates?: MailTemplate[];
}) {
  const router = useRouter();
  const isQueue = view === "queue" && !search.active;   // Coda (to-do): i triati spariscono
  const isTriage = (view === "queue" || view === "all") || search.active; // triage attivo anche sui risultati
  const sp = scopeAll ? "&scope=all" : "";
  const hrefView = (v: InboxView) => `/inbox?view=${v}${sp}`;          // pulisce anche la ricerca
  const hrefScope = (all: boolean) => `/inbox?view=${view}${all ? "&scope=all" : ""}${search.q ? `&q=${encodeURIComponent(search.q)}` : ""}${search.sender ? `&sender=${encodeURIComponent(search.sender)}` : ""}${search.partner ? `&partner=${search.partner}` : ""}`;
  const hrefSearch = (q: string) => `/inbox?view=${view}${sp}&q=${encodeURIComponent(q)}`;
  const hrefSender = (email: string) => `/inbox?view=${view}${sp}&sender=${encodeURIComponent(email)}`;
  const hrefPartner = (id: number) => `/inbox?view=${view}${sp}&partner=${id}`;
  const [searchInput, setSearchInput] = useState(search.q);
  const [selectedId, setSelectedId] = useState(initialSelectedId);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [snack, setSnack] = useState<Snack>(null);
  const [confirmTrash, setConfirmTrash] = useState<number[] | null>(null); // ids da cestinare (sel/gruppo caricati)
  const [confirmSender, setConfirmSender] = useState<SenderTarget | null>(null); // cestina-mittente server-side
  const [groupMode, setGroupMode] = useState<GroupMode>("date");
  const [groupSort, setGroupSort] = useState<"recency" | "volume">("recency");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [bodyHtml, setBodyHtml] = useState<string>("");
  const [bodyLoading, setBodyLoading] = useState(false);
  const [composer, setComposer] = useState<{ mode: ComposerMode; target: ComposerTarget } | null>(null);
  const EMPTY_TARGET: ComposerTarget = { id: 0, subject: "", senderEmail: "", senderName: "" };

  const item = items.find((i) => i.id === selectedId) ?? items[0];
  // Brief B perf: bundle lazy. Il server pre-carica solo il selezionato; gli altri si
  // caricano on-demand alla selezione (prima si prefetchavano 12 = ~1s sprecato a ogni apertura inbox).
  const [bundleMap, setBundleMap] = useState<Record<number, PartnerBundle>>(bundles);
  const bundle = item?.partnerId ? (bundleMap[item.partnerId] ?? null) : null;
  const m = item?.message;

  useEffect(() => {
    const pid = item?.partnerId;
    if (!pid || bundleMap[pid]) return;
    let alive = true;
    fetch(`${BP}/api/console/partner-bundle`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ partnerId: pid }) })
      .then((r) => r.json())
      .then((b) => { if (alive && b && b.partner) setBundleMap((prev) => ({ ...prev, [pid]: b })); })
      .catch(() => {});
    return () => { alive = false; };
  }, [item?.partnerId, bundleMap]);

  // TARGET azioni Bar B: selezione se ≥1, altrimenti la mail aperta.
  const targetIds = useCallback((): number[] => {
    if (checked.size) return [...checked];
    return item ? [item.id] : [];
  }, [checked, item]);
  const targetCount = checked.size || (item ? 1 : 0);

  // corpo completo on-select.
  useEffect(() => {
    if (!item) { setBodyHtml(""); return; }
    let alive = true;
    setBodyLoading(true); setBodyHtml("");
    fetch(`${BP}/api/console/message?id=${item.id}`).then((r) => r.json())
      .then((j) => { if (alive) setBodyHtml(j.ok ? (j.bodyHtml ?? "") : ""); })
      .catch(() => { if (alive) setBodyHtml(""); })
      .finally(() => { if (alive) setBodyLoading(false); });
    return () => { alive = false; };
  }, [item]);

  const composerTarget = useCallback((): ComposerTarget | null => {
    if (!item || !m) return null;
    return { id: item.id, subject: m.subject, senderEmail: m.senderEmail || item.senderEmail, senderName: m.senderName, accountId: item.accountId };
  }, [item, m]);
  const openReply = useCallback(() => { const t = composerTarget(); if (t) setComposer({ mode: "reply", target: t }); }, [composerTarget]);
  const openForward = useCallback(() => { const t = composerTarget(); if (t) setComposer({ mode: "forward", target: t }); }, [composerTarget]);

  const allChecked = items.length > 0 && checked.size === items.length;
  const toggle = (id: number) => setChecked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const setMany = (ids: number[], on: boolean) => setChecked((s) => { const n = new Set(s); ids.forEach((i) => (on ? n.add(i) : n.delete(i))); return n; });
  const selectAll = () => setChecked(allChecked ? new Set() : new Set(items.map((i) => i.id)));

  const doTriage = useCallback(async (state: string, idsArg?: number[]) => {
    const ids = idsArg ?? targetIds();
    if (!ids.length) return;
    const idset = new Set(ids);
    const prev: Record<number, string> = {};
    items.forEach((i) => { if (idset.has(i.id)) prev[i.id] = i.state; });
    setBusy(true);
    const r = await postJson("/api/console/triage", { ids, state });
    setBusy(false); setConfirmTrash(null);
    if (!r.ok) { setSnack({ text: `Errore: ${r.message ?? "triage fallito"}`, prev: {} }); return; }
    const verb = state === "keep" ? "tenuti" : state === "discard" ? "scartati" : state === "trash" ? "cestinati" : "ripristinati";
    // AUTO-ADVANCE: salta alla prossima mail in coda NON triata (le triate spariscono al refresh).
    const curIdx = items.findIndex((i) => i.id === selectedId);
    const after = items.slice(curIdx + 1).find((i) => !idset.has(i.id));
    const remaining = items.filter((i) => !idset.has(i.id));
    setSelectedId(after ? after.id : remaining.length ? remaining[remaining.length - 1].id : 0);
    setChecked(new Set());
    setSnack({ text: `${ids.length} ${verb}`, prev });
    router.refresh();
  }, [targetIds, items, router, selectedId]);

  const doMarkRead = useCallback(async (isRead: boolean) => {
    const ids = targetIds();
    if (!ids.length) return;
    setBusy(true);
    const r = await postJson("/api/console/read", { ids, isRead });
    setBusy(false);
    setSnack({ text: r.ok ? `${ids.length} segnate ${isRead ? "lette" : "non lette"}` : `Errore: ${r.message ?? "fallito"}`, prev: {} });
    setChecked(new Set());
    router.refresh();
  }, [targetIds, router]);

  // Nuke-all per mittente SERVER-SIDE: triaga TUTTE le mail del mittente entro scope+vista,
  // non solo i caricati. Ritorna prev di TUTTO il set per l'undo completo.
  const triageSender = useCallback(async (state: string, t: SenderTarget) => {
    setBusy(true);
    const r = await postJson("/api/console/triage-sender", { state, partnerId: t.partnerId, senderEmail: t.senderEmail, view, scopeAll }) as { ok: boolean; message?: string; count?: number; prev?: Record<number, string> };
    setBusy(false); setConfirmSender(null);
    if (!r.ok) { setSnack({ text: `Errore: ${r.message ?? "fallito"}`, prev: {} }); return; }
    const verb = state === "keep" ? "tenuti" : state === "discard" ? "scartati" : state === "trash" ? "cestinati" : "ripristinati";
    setChecked(new Set());
    setSnack({ text: `${r.count ?? 0} ${verb} (${t.label})`, prev: r.prev ?? {} });
    router.refresh();
  }, [view, scopeAll, router]);

  async function undo() {
    if (!snack || !Object.keys(snack.prev).length) { setSnack(null); return; }
    const byState = new Map<string, number[]>();
    for (const [id, st] of Object.entries(snack.prev)) {
      const arr = byState.get(st);
      if (arr) arr.push(Number(id)); else byState.set(st, [Number(id)]);
    }
    setBusy(true);
    for (const [st, ids] of byState) await postJson("/api/console/triage", { ids, state: st });
    setBusy(false); setSnack(null);
    router.refresh();
  }

  // J/K navigazione, X selezione corrente.
  const move = useCallback((dir: 1 | -1) => {
    if (!items.length) return;
    const idx = items.findIndex((i) => i.id === selectedId);
    const next = Math.max(0, Math.min(items.length - 1, (idx < 0 ? 0 : idx) + dir));
    setSelectedId(items[next].id);
  }, [items, selectedId]);

  // SCORCIATOIE — disattive se composer aperto o focus in input/textarea/contentEditable.
  useEffect(() => {
    function typing(): boolean {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return false;
      const tag = el.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
    }
    function onKey(e: KeyboardEvent) {
      if (composer || typing() || e.metaKey || e.ctrlKey || e.altKey) return;
      switch (e.key) {
        case "F8": case "r": case "R": if (isTriage) { e.preventDefault(); openReply(); } break;
        case "t": case "T": if (isTriage) { e.preventDefault(); doTriage("keep"); } break;
        case "s": case "S": if (isTriage) { e.preventDefault(); doTriage("discard"); } break;
        case "Backspace": if (isTriage && targetCount) { e.preventDefault(); setConfirmTrash(targetIds()); } break;
        case "j": case "J": e.preventDefault(); move(1); break;
        case "k": case "K": e.preventDefault(); move(-1); break;
        case "x": case "X": if (item) { e.preventDefault(); toggle(item.id); } break;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [composer, view, openReply, doTriage, move, item, targetCount]);

  // raggruppamento: "date" = lista piatta (data desc); "casella" = per account;
  // "mittente" = per partner se linkato, altrimenti email_from (stessa logica del filtro Slice 2).
  const groups = useMemo<GroupRec[]>(() => {
    if (groupMode === "date") return [{ key: "_all", label: "", items, lastDate: "" }];
    const map = new Map<string, GroupRec>();
    for (const it of items) {
      let key: string, label: string;
      if (groupMode === "casella") { key = `c:${it.accountName}`; label = it.accountName || "— senza casella"; }
      else if (it.partnerId) { key = `p:${it.partnerId}`; label = it.org || it.senderEmail || "—"; }
      else { key = `e:${it.senderEmail}`; label = it.senderEmail || "— senza mittente"; }
      const g = map.get(key);
      if (g) { g.items.push(it); if (it.message.timeLabel > g.lastDate) g.lastDate = it.message.timeLabel; }
      else map.set(key, { key, label, items: [it], lastDate: it.message.timeLabel });
    }
    const arr = [...map.values()];
    if (groupMode === "mittente") {
      arr.sort((a, b) => groupSort === "volume" ? b.items.length - a.items.length : b.lastDate.localeCompare(a.lastDate));
    }
    return arr;
  }, [items, groupMode, groupSort]);

  const triageDisabled = busy || targetCount === 0;
  const btn = (extra?: React.CSSProperties): React.CSSProperties => ({ padding: "5px 9px", fontSize: 12, ...extra });

  return (
    <>
      {/* Pane 2: lista */}
      <div style={{ width: 270, flexShrink: 0, borderRight: "1px solid var(--line)", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
        {/* nav PRIMARIA: Coda (badge) + Inbox · bucket nel menu Altro */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--line)", fontSize: 11, alignItems: "stretch" }}>
          {PRIMARY_TABS.map((t) => (
            <Link key={t.key} href={hrefView(t.key)} style={{ flex: 1, textAlign: "center", padding: "7px 0", textDecoration: "none", background: view === t.key ? "var(--accent-t)" : "transparent", color: view === t.key ? "var(--accent)" : "var(--muted)", fontWeight: view === t.key ? 700 : 400, display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
              {t.label}{t.key === "queue" && queueCount > 0 ? <span className="cnt" style={{ background: "var(--accent)", color: "#fff", borderRadius: 9, fontSize: 9, padding: "0 5px" }}>{queueCount}</span> : null}
            </Link>
          ))}
          <div style={{ display: "flex", alignItems: "center", padding: "0 4px", borderLeft: "1px solid var(--line)" }}>
            <More>
              {BUCKET_TABS.map((t) => (
                <Link key={t.key} href={hrefView(t.key)} className="btn" style={{ fontSize: 12, justifyContent: "flex-start", textDecoration: "none", color: view === t.key ? "var(--accent)" : "var(--ink)" }}>{t.label}</Link>
              ))}
            </More>
          </div>
        </div>
        {/* scope per-operatore: Solo me (default) / Tutte (toggle esplicito) */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--line)", fontSize: 10, alignItems: "center", padding: "4px 8px", gap: 6 }}>
          <span className="muted">Casella:</span>
          <Link href={hrefScope(false)} style={{ textDecoration: "none", fontWeight: !scopeAll ? 700 : 400, color: !scopeAll ? "var(--accent)" : "var(--muted)" }}>Solo me</Link>
          <span className="muted">·</span>
          <Link href={hrefScope(true)} style={{ textDecoration: "none", fontWeight: scopeAll ? 700 : 400, color: scopeAll ? "var(--accent)" : "var(--muted)" }}>Tutte</Link>
          <span style={{ flex: 1 }} />
          {groupMode === "mittente" ? (
            <button onClick={() => setGroupSort((s) => s === "recency" ? "volume" : "recency")} title="Ordina gruppi" style={{ border: "none", cursor: "pointer", background: "none", color: "var(--muted)" }}>↕ {groupSort === "recency" ? "recenti" : "volume"}</button>
          ) : null}
          {(["date", "casella", "mittente"] as GroupMode[]).map((g) => (
            <button key={g} onClick={() => setGroupMode(g)} style={{ border: "none", cursor: "pointer", background: "none", color: groupMode === g ? "var(--accent)" : "var(--muted)", fontWeight: groupMode === g ? 700 : 400 }}>{g === "date" ? "data" : g === "casella" ? "casella" : "mittente"}</button>
          ))}
        </div>
        {/* barra ricerca full-record scoped (server-side, paginata) */}
        <form onSubmit={(e) => { e.preventDefault(); router.push(searchInput.trim() ? hrefSearch(searchInput.trim()) : hrefView(view)); }}
          style={{ display: "flex", gap: 6, padding: "6px 8px", borderBottom: "1px solid var(--line)" }}>
          <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Cerca in tutto il record…"
            style={{ flex: 1, padding: "5px 8px", border: "1px solid var(--line)", borderRadius: 6, fontSize: 12 }} />
          <button type="submit" className="btn" style={{ fontSize: 12 }}>🔍</button>
        </form>
        {/* chip ricerca/mittente attivo → x torna al tab */}
        {search.active ? (
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 8px", borderBottom: "1px solid var(--line)", background: "var(--accent-t)", fontSize: 11 }}>
            <span className="grow" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {search.partner ? "Partner selezionato" : search.sender ? `Mittente: ${search.sender}` : `Ricerca: "${search.q}"`} · {items.length} risultati
            </span>
            <Link href={hrefView(view)} onClick={() => setSearchInput("")} style={{ textDecoration: "none", color: "var(--accent)", fontWeight: 700 }}>✕</Link>
          </div>
        ) : null}
        <div style={{ overflowY: "auto", flex: 1 }}>
          {groups.map((g) => {
            const its = g.items;
            const groupIds = its.map((i) => i.id);
            const groupAll = its.length > 0 && its.every((i) => checked.has(i.id));
            const isCollapsed = collapsed.has(g.key);
            const bySender = groupMode === "mittente";
            // conteggio VERO (read_group) se disponibile, altrimenti i caricati.
            const trueCount = (bySender && !search.active && senderCounts[g.key] != null) ? senderCounts[g.key] : its.length;
            // target server-side dal key del gruppo (p:<id> | e:<email>).
            const senderTarget: SenderTarget = g.key.startsWith("p:")
              ? { partnerId: Number(g.key.slice(2)), label: g.label, count: trueCount }
              : { senderEmail: g.key.slice(2), label: g.label, count: trueCount };
            const groupServerOk = bySender && !search.active; // nuke-all server-side solo su Coda/Inbox/bucket
            return (
              <div key={g.key}>
                {g.label ? (
                  <div style={{ padding: "6px 10px", background: "var(--panel-2)", display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--muted)", borderTop: "1px solid var(--line)" }}>
                    <input type="checkbox" checked={groupAll} onChange={() => setMany(groupIds, !groupAll)} title="Seleziona gruppo (caricati)" />
                    <button onClick={() => setCollapsed((s) => { const n = new Set(s); if (n.has(g.key)) n.delete(g.key); else n.add(g.key); return n; })} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--muted)", padding: 0 }}>{isCollapsed ? "▸" : "▾"}</button>
                    <span style={{ flex: 1, minWidth: 0, color: "var(--ink)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.label}</span>
                    <span className="chip" style={{ background: "var(--accent-t)", color: "var(--accent)" }} title={trueCount !== its.length ? `${its.length} caricate di ${trueCount}` : undefined}>{trueCount}</span>
                    {bySender ? <span style={{ fontSize: 9, flexShrink: 0 }}>{g.lastDate}</span> : null}
                    {/* azioni sul gruppo INTERO (server-side nuke-all su Coda/Inbox) */}
                    {bySender && isTriage ? (
                      <span className="row" style={{ gap: 3, flexShrink: 0 }}>
                        <button className="btn" style={btn({ fontSize: 10, padding: "2px 5px", background: "var(--ok-t)", color: "var(--ok)" })} disabled={busy} title="Tieni tutto il mittente" onClick={() => groupServerOk ? triageSender("keep", senderTarget) : doTriage("keep", groupIds)}>★</button>
                        <button className="btn" style={btn({ fontSize: 10, padding: "2px 5px" })} disabled={busy} title="Scarta tutto il mittente" onClick={() => groupServerOk ? triageSender("discard", senderTarget) : doTriage("discard", groupIds)}>✕</button>
                        <button className="btn" style={btn({ fontSize: 10, padding: "2px 5px", background: "var(--danger-t)", color: "var(--danger)" })} disabled={busy} title="Cestina tutto il mittente" onClick={() => groupServerOk ? setConfirmSender(senderTarget) : setConfirmTrash(groupIds)}>🗑</button>
                      </span>
                    ) : null}
                  </div>
                ) : null}
                {isCollapsed ? null : its.map((it) => {
                  const sel = it.id === selectedId; const ck = checked.has(it.id);
                  return (
                    <div key={it.id} style={{ padding: "9px 12px", display: "flex", gap: 8, borderLeft: `3px solid ${sel ? "var(--accent)" : "transparent"}`, background: ck ? "var(--accent-t)" : sel ? "var(--panel-2)" : "transparent" }}>
                      <input type="checkbox" checked={ck} onChange={() => toggle(it.id)} style={{ marginTop: 3 }} />
                      <div style={{ flex: 1, minWidth: 0, cursor: "pointer" }} onClick={() => setSelectedId(it.id)}>
                        <div className="row" style={{ gap: 6, justifyContent: "space-between" }}>
                          <span style={{ display: "flex", gap: 6, alignItems: "center", minWidth: 0 }}>
                            <span className="opdot" style={{ background: operatorColor[it.operator] }} />
                            <span style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.name}</span>
                          </span>
                          <span className="muted" style={{ fontSize: 10, flexShrink: 0 }}>{it.message.timeLabel}</span>
                        </div>
                        <div className="muted" style={{ fontSize: 11, margin: "2px 0 4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {groupMode === "date" && it.accountName ? <span title="casella">{it.accountName} · </span> : null}{it.message.subject}
                        </div>
                        <span className="row" style={{ gap: 4 }}>
                          {/* stato della mail (così nei risultati/Inbox sai dov'è) */}
                          {(search.active || !isQueue) ? (() => { const c = stateChip(it.state); return <span className="chip" style={toneStyle(c.tone)}>{c.label}</span>; })() : null}
                          {it.badgeLabel ? <span className="chip" style={toneStyle(it.badgeTone)}>{it.badgeLabel}</span> : null}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
          {items.length === 0 ? <div className="muted" style={{ padding: 16, fontSize: 12 }}>{isQueue ? "Coda vuota: tutto triato." : view === "all" ? "Inbox vuota." : "Vuoto."}</div> : null}
        </div>
      </div>

      {/* Pane 3: barre sticky + corpo + contesto */}
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* BARRE STICKY */}
        <div style={{ position: "sticky", top: 0, zIndex: 10, margin: "-1px 0 0", background: "var(--canvas, #FAFAF8)" }}>
          {/* BAR B — fissa: triage + selezione (target = selezione o mail aperta) */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", padding: "7px 10px", borderBottom: "1px solid var(--line)", background: "var(--paper)" }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>{checked.size ? `${checked.size} selezionate` : item ? "mail aperta" : "—"}</span>
            <button className="btn" style={btn()} onClick={selectAll}>{allChecked ? "Deseleziona" : "Seleziona tutto"}</button>
            <span style={{ width: 1, height: 18, background: "var(--line)", margin: "0 2px" }} />
            {!isTriage ? (
              <button className="btn" style={btn()} disabled={triageDisabled} onClick={() => doTriage("review")}>↩ Ripristina in coda</button>
            ) : (
              <>
                <button className="btn" style={btn({ background: "var(--ok-t)", color: "var(--ok)" })} disabled={triageDisabled} onClick={() => doTriage("keep")}>★ Tieni</button>
                <button className="btn" style={btn()} disabled={triageDisabled} onClick={() => doTriage("discard")}>✕ Scarta</button>
                <button className="btn" style={btn({ background: "var(--danger-t)", color: "var(--danger)" })} disabled={triageDisabled} onClick={() => setConfirmTrash(targetIds())}>🗑 Cestina</button>
              </>
            )}
            <button className="btn" style={btn()} disabled={triageDisabled} onClick={() => doMarkRead(true)}>✉ Segna lette</button>
            {/* Nuova mail SEMPRE disponibile (compose da zero) */}
            <button className="btn pri" style={btn()} onClick={() => setComposer({ mode: "new", target: EMPTY_TARGET })}>✎ Nuova mail</button>
            <span style={{ flex: 1 }} />
            <More>
              {item ? <CreateLeadButton name={`Nuovo contatto · ${m?.senderName || m?.senderEmail || ""}`} emailFrom={m?.senderEmail} /> : null}
              <button className="btn" style={btn()} disabled title="Prossimamente">⛔ Blocca mittente</button>
            </More>
          </div>

          {/* BAR A — contestuale: azioni della mail aperta */}
          {item && m && isTriage ? (
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", padding: "7px 10px", borderBottom: "1px solid var(--line)", background: "var(--panel-2)" }}>
              <span className="muted" style={{ fontSize: 11, marginRight: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 240 }}>
                <b style={{ color: "var(--ink)" }}>{m.senderName || m.senderEmail}</b>{item.accountName ? ` · casella ${item.accountName}` : ""}
              </span>
              <span style={{ flex: 1 }} />
              <button className="btn pri" style={btn()} onClick={openReply}><Icon name="reply" size={13} /> Rispondi · R</button>
              <button className="btn" style={btn()} onClick={openForward}>↪ Inoltra</button>
              <AiDraftButton subject={m.subject} body={m.body} partnerName={m.senderName} to={m.senderEmail} />
              <LinkLeadButton messageId={item.id} leadId={bundle?.leads[0]?.id ?? null} leadName={bundle?.leads[0]?.name} />
              <More>
                <button className="btn" style={btn()} onClick={() => doMarkRead(false)}>✉ Segna non letta</button>
              </More>
            </div>
          ) : null}
        </div>

        {/* corpo mail (senza tasti in fondo: vivono in Bar A) */}
        {!item || !m ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest"><span>{isTriage ? "Nessuna mail aperta." : "Vuoto."}</span></div>
          </div>
        ) : (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.subject || "(senza oggetto)"}</div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 11 }}>
              <span style={{ color: "var(--ink)", fontWeight: 600 }}>{m.senderName}</span> · {m.senderEmail} · {m.timeLabel}
              {item.accountName ? <span> · casella <b>{item.accountName}</b></span> : null}
              {/* filtro per mittente/partner: tutte le mail di questo contatto */}
              <Link href={item.partnerId ? hrefPartner(item.partnerId) : hrefSender(m.senderEmail || item.senderEmail)}
                style={{ marginLeft: 8, color: "var(--accent)", textDecoration: "none" }} title="Tutte le mail di questo mittente/partner">⛓ tutte di questo mittente</Link>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.6, maxHeight: 420, overflowY: "auto", borderTop: "1px solid var(--line)", paddingTop: 10 }}>
              {bodyLoading ? <span className="muted">caricamento corpo…</span> : bodyHtml ? <div dangerouslySetInnerHTML={{ __html: bodyHtml }} /> : <span>{m.body || "(nessun corpo)"}</span>}
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
                  <Icon name="check" size={13} color="var(--ok)" /> riconosciuto · match {item.resolutionMatch === "domain" ? "dominio " : item.resolutionMatch === "exact" ? "esatto " : ""}
                  <span style={{ fontFamily: "var(--mono)" }}>{bundle.partner.domain ?? bundle.partner.email}</span>
                </div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              <Cell label="Lead" value={bundle.leads[0] ? `${bundle.leads[0].stage ?? "lead"} · score ${bundle.leads[0].score ?? "n/d"}` : null} empty="Nessun lead" accent={!!bundle.leads[0]} href={bundle.leads[0] ? `/lead/${bundle.leads[0].id}` : undefined} />
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
            <PartnerMailThread messages={bundle.mailThread} title="Mail con questo partner" limit={5} />
          </div>
        ) : item && m ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest"><span>Mittente non riconosciuto: nessun partner collegato.</span></div>
            <div style={{ marginTop: 10 }}><PartnerMailThread messages={[]} title="Mail con questo partner" /></div>
          </div>
        ) : null}
      </main>

      {composer ? <Composer mode={composer.mode} target={composer.target} accounts={accounts} library={library} templates={templates} onClose={() => setComposer(null)} /> : null}

      {confirmTrash ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={() => setConfirmTrash(null)}>
          <div className="card" style={{ padding: 22, width: 320 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Cestina {confirmTrash.length} {confirmTrash.length === 1 ? "messaggio" : "messaggi"}?</div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>Vanno nel Cestino (recuperabili). Nessuna cancellazione fisica.</div>
            <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
              <button className="btn" onClick={() => setConfirmTrash(null)}>Annulla</button>
              <button className="btn" disabled={busy} style={{ background: "var(--danger-t)", color: "var(--danger)" }} onClick={() => doTriage("trash", confirmTrash)}>🗑 Cestina</button>
            </div>
          </div>
        </div>
      ) : null}

      {/* conferma nuke-all per mittente (totale VERO server-side) */}
      {confirmSender ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={() => setConfirmSender(null)}>
          <div className="card" style={{ padding: 22, width: 340 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Cestina {confirmSender.count} di {confirmSender.label}?</div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>TUTTE le mail di questo mittente nella vista corrente (entro la tua casella). Nel Cestino, recuperabili. Nessuna cancellazione fisica.</div>
            <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
              <button className="btn" onClick={() => setConfirmSender(null)}>Annulla</button>
              <button className="btn" disabled={busy} style={{ background: "var(--danger-t)", color: "var(--danger)" }} onClick={() => triageSender("trash", confirmSender)}>🗑 Cestina tutto</button>
            </div>
          </div>
        </div>
      ) : null}

      {snack ? (
        <div style={{ position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)", background: "var(--ink)", color: "#fff", padding: "10px 14px", borderRadius: 8, display: "flex", gap: 14, alignItems: "center", zIndex: 60, boxShadow: "0 4px 16px rgba(0,0,0,.25)" }}>
          <span style={{ fontSize: 13 }}>{snack.text}</span>
          {Object.keys(snack.prev).length ? <button onClick={undo} disabled={busy} style={{ background: "none", border: "none", color: "#9ec46a", fontWeight: 700, cursor: "pointer" }}>Annulla</button> : null}
          <button onClick={() => setSnack(null)} style={{ background: "none", border: "none", color: "#aaa", cursor: "pointer" }}>✕</button>
        </div>
      ) : null}
    </>
  );
}

function Cell({ label, value, empty, accent, href }: { label: string; value: string | null; empty: string; accent: boolean; href?: string }) {
  const text = (<div style={{ fontWeight: 600, fontSize: 13, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}{href ? " →" : ""}</div>);
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
