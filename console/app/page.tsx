// Regia — command center (schermo 1 di console_reference_v4). Home della console.
import Link from "next/link";
import { getRegia, getOperatorAccounts, getLibrary, getTemplates } from "@/lib/bundle";
import { auth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { Icon } from "@/components/Icons";
import { operatorColor } from "@/lib/theme";
import { moneyCompact, EmptyHonest } from "@/components/Honest";
import { QuickTaskBar } from "@/components/QuickTaskBar";
import { ActionBar } from "@/components/ActionBar";
import { PipelineSnapshot } from "@/components/PipelineSnapshot";
import type { Tone } from "@/lib/types";

export const dynamic = "force-dynamic";

function toneStyle(tone: Tone): React.CSSProperties {
  switch (tone) {
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}

export default async function Regia() {
  const session = await auth();
  const [r, accounts, library, templates] = await Promise.all([
    getRegia(),
    getOperatorAccounts({ operatorUid: session?.operatorUid }),
    getLibrary(),
    getTemplates(),
  ]);

  return (
    <div className="app">
      <Sidebar active="regia" source={r.source === "mock" ? "mock" : "Odoo · folinofood"} />
      <main className="main">
        <h2 style={{ fontSize: 19 }}>Buongiorno {r.greetingName}</h2>
        <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
          {r.subtitle || `${r.queue.length} elementi ti aspettano`}
        </div>

        {/* Barra azioni rapide (azione-first) — ogni verbo monta il PartnerPicker condiviso */}
        <ActionBar accounts={accounts} library={library} templates={templates} />
        <QuickTaskBar />

        {/* 4 KPI */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 20 }}>
          <div className="kpi"><div className="k">Lead caldi</div><div className="v">{r.kpis.hotLeads}</div></div>
          <div className="kpi"><div className="k">Follow-up scaduti</div><div className="v" style={{ color: "var(--danger)" }}>{r.kpis.overdueFollowups}</div></div>
          <div className="kpi"><div className="k">Dossier bloccati</div><div className="v" style={{ color: "var(--warn)" }}>{r.kpis.blockedDossiers}</div></div>
          <div className="kpi"><div className="k">Fatturato giugno</div><div className="v">{moneyCompact(r.kpis.monthRevenue)}</div></div>
        </div>

        {/* Coda "Ti aspetta" */}
        <h3 className="sec-title">Ti aspetta</h3>
        <div className="card" style={{ overflow: "hidden", marginBottom: 18 }}>
          {r.queue.length === 0 ? (
            <div style={{ padding: 12 }}><EmptyHonest label="Nessuna email in attesa di risposta." actionLabel="Apri inbox" /></div>
          ) : (
            r.queue.map((q, i) => (
              <Link key={i} href={q.partnerId ? `/partner/${q.partnerId}` : "/inbox"}
                className="row" style={{ padding: "10px 13px", borderBottom: i < r.queue.length - 1 ? "1px solid var(--line)" : "none" }}>
                <span className="opdot" style={{ background: operatorColor[q.operator] }} />
                <span style={{ fontWeight: 600, width: 150, flexShrink: 0 }}>{q.partnerName}</span>
                <span className="muted grow ell" style={{ fontSize: 13 }}>{q.subject}</span>
                <span className="chip" style={toneStyle(q.badgeTone)}>{q.badgeLabel}</span>
              </Link>
            ))
          )}
        </div>

        {/* Barra pipeline (riassunto statico) */}
        <div className="row" style={{ marginBottom: 14 }}>
          <h3 className="sec-title" style={{ margin: 0 }}>Pipeline</h3>
          {r.pipeline.segments.length === 0 ? (
            <span className="muted" style={{ fontSize: 12 }}>nessun lead in pipeline</span>
          ) : (
            <>
              <div className="grow" style={{ display: "flex", height: 9, borderRadius: 999, overflow: "hidden" }}>
                {r.pipeline.segments.map((s, i) => (
                  <div key={i} title={`${s.label} ${s.pct}%`} style={{ width: `${s.pct}%`, background: s.color }} />
                ))}
              </div>
              <span className="muted" style={{ fontSize: 12 }}>{r.pipeline.totalLeads} lead</span>
            </>
          )}
        </div>

        {/* Fase 2 WI-D — snapshot pipeline azionabile (click stage → deal → avanza) */}
        <PipelineSnapshot />
      </main>
    </div>
  );
}
