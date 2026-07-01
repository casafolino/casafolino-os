"use client";
// Dossier cliente — vista unica (Brief). Header + 4 metric card + 4 azioni precompilate +
// timeline unica cronologica (ordini, mail, task, campioni, note) mescolati per data, paginata.
import { useCallback, useEffect, useState } from "react";
import {
  getPartnerDossier, getPartnerTimeline, semaforoColor, timelineColor, timelineIcon, money,
  type DossierHeader, type TimelineItem,
} from "@/lib/regia";
import { DossierActions } from "@/components/DossierActions";
import type { Account } from "@/components/Composer";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";

const SEMAFORO_LABEL: Record<string, string> = {
  fresh: "Attivo", warning: "Da seguire", danger: "Fermo", neutral: "Nessuna attività",
};

function fmtDate(iso: string): string {
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      {sub ? <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{sub}</div> : null}
    </div>
  );
}

export function DossierClient({
  partnerId, accounts, library, templates,
}: {
  partnerId: number;
  accounts: Account[];
  library: LibraryItem[];
  templates: MailTemplate[];
}) {
  const [head, setHead] = useState<DossierHeader | null>(null);
  const [headErr, setHeadErr] = useState<string | null>(null);
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tlErr, setTlErr] = useState<string | null>(null);
  const PAGE = 25;

  useEffect(() => {
    getPartnerDossier(partnerId)
      .then((r) => { if (r?.message) setHeadErr(r.message); else setHead(r); })
      .catch((e) => setHeadErr((e as Error).message));
  }, [partnerId]);

  const loadPage = useCallback(async (off: number) => {
    setLoading(true); setTlErr(null);
    try {
      const r = await getPartnerTimeline(partnerId, PAGE, off);
      if (r?.message) { setTlErr(r.message); return; }
      setItems((prev) => (off === 0 ? r.items : [...prev, ...r.items]));
      setHasMore(!!r.hasMore);
      setOffset(off + (r.items?.length ?? 0));
    } catch (e) { setTlErr((e as Error).message); } finally { setLoading(false); }
  }, [partnerId]);

  useEffect(() => { loadPage(0); }, [loadPage]);

  const m = head?.metrics;
  const sem = head?.semaforo ?? "neutral";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 860 }}>
      {/* Header */}
      <div className="card" style={{ padding: 18 }}>
        {headErr ? <div className="muted" style={{ fontSize: 12, color: "var(--danger)" }}>{headErr}</div> : null}
        <div className="row" style={{ gap: 12, alignItems: "center" }}>
          <span className="opdot" title={SEMAFORO_LABEL[sem]} style={{ width: 12, height: 12, background: semaforoColor[sem] }} />
          <h2 style={{ fontSize: 22, margin: 0 }}>{head?.partner.name ?? "…"}</h2>
          {head?.partner.owner ? (
            <span className="av" title={`Owner: ${head.partner.owner}`} style={{ width: 26, height: 26, fontSize: 11 }}>{head.partner.ownerInitials}</span>
          ) : null}
        </div>
        <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
          {[head?.partner.city, head?.partner.country, head?.partner.email].filter(Boolean).join(" · ")}
        </div>
        <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 10 }}>
          <span className="chip" style={{ background: semaforoColor[sem] + "22", color: semaforoColor[sem] }}>
            {SEMAFORO_LABEL[sem]}{head?.semaforoDays != null ? ` · ${head.semaforoDays} gg` : ""}
          </span>
          {(head?.tags ?? []).map((t, i) => <span key={i} className="chip">{t}</span>)}
        </div>
      </div>

      {/* 4 metric card */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }}>
        <MetricCard
          label="Ultimo ordine"
          value={m?.ultimoOrdine ? money(m.ultimoOrdine.amount) : "—"}
          sub={m?.ultimoOrdine?.date ? fmtDate(m.ultimoOrdine.date) : (head ? "nessun ordine" : "")}
        />
        <MetricCard label="Fatturato 12 mesi" value={m ? money(m.fatturato12m) : "—"} />
        <MetricCard label="Stage" value={m?.stage ?? "—"} sub={m?.stage ? "opportunità aperta" : (head ? "nessuna opp." : "")} />
        <MetricCard label="Task aperti" value={m ? String(m.taskAperti) : "—"} />
      </div>

      {/* 4 azioni precompilate */}
      {head ? (
        <DossierActions
          partnerId={partnerId}
          companyName={head.partner.name}
          accounts={accounts}
          library={library}
          templates={templates}
        />
      ) : null}

      {/* Timeline unica cronologica */}
      <div>
        <h3 className="sec-title">Cronologia</h3>
        {tlErr ? <div className="card" style={{ padding: 12 }}><span className="muted" style={{ fontSize: 12, color: "var(--danger)" }}>{tlErr}</span></div> : null}
        {!tlErr && items.length === 0 && !loading ? (
          <div className="card" style={{ padding: 12 }}><span className="muted" style={{ fontSize: 12 }}>Nessun evento nella cronologia.</span></div>
        ) : null}
        <div className="card" style={{ padding: "6px 14px" }}>
          {items.map((it, i) => (
            <div key={i} className="tl-item" style={{ borderBottom: i < items.length - 1 ? "1px solid var(--line)" : "none", padding: "10px 0" }}>
              <span title={it.type} style={{ width: 22, height: 22, borderRadius: 999, background: timelineColor[it.type] + "22", color: timelineColor[it.type], display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0 }}>
                {timelineIcon[it.type]}
              </span>
              <div className="grow" style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.title}</div>
                {it.subtitle ? <div className="muted" style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.subtitle}</div> : null}
              </div>
              <div className="muted" style={{ fontSize: 11, flexShrink: 0, textAlign: "right" }}>
                {fmtDate(it.date)}
                {it.author ? <div style={{ opacity: 0.8 }}>{it.author}</div> : null}
              </div>
            </div>
          ))}
        </div>
        <div className="row" style={{ justifyContent: "center", marginTop: 10 }}>
          {loading ? <span className="muted" style={{ fontSize: 12 }}>Carico…</span>
            : hasMore ? <button className="btn-secondary" onClick={() => loadPage(offset)}>Carica altri</button>
            : items.length > 0 ? <span className="muted" style={{ fontSize: 11 }}>— fine cronologia —</span> : null}
        </div>
      </div>
    </div>
  );
}
