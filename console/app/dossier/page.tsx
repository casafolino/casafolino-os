// Dossier 360 (schermo 4). Server: header + KPI; client DossierTabs per i tab.
import { getDossier, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { DossierTabs } from "@/components/DossierTabs";
import { moneyCompact } from "@/components/Honest";
import { operatorColor, operatorLabel } from "@/lib/theme";
import type { Tone } from "@/lib/types";

export const dynamic = "force-dynamic";

function tone(t: Tone): React.CSSProperties {
  switch (t) {
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}
function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

export default async function DossierPage() {
  const d = await getDossier();
  const bundle = d.partnerId ? await getPartnerBundle(d.partnerId) : null;

  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main">
        <div className="row" style={{ gap: 10, marginBottom: 14 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--ok-t)", color: "var(--ok)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, flexShrink: 0 }}>{initials(d.partnerName)}</div>
          <div className="grow">
            <div style={{ fontWeight: 600, fontSize: 15 }}>{d.name} <span className="chip" style={tone(d.statusTone)}>{d.status}</span></div>
            <div className="muted" style={{ fontSize: 12 }}>
              {d.partnerName}{d.country ? ` · ${d.country}` : ""} · seguito da <span style={{ color: operatorColor[d.operator], fontWeight: 600 }}>{operatorLabel[d.operator]}</span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="muted" style={{ fontSize: 11 }}>Valore stimato</div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>{d.valueEstimate != null ? moneyCompact(d.valueEstimate) : "da stimare"}</div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8, marginBottom: 16 }}>
          <div className="kpi" style={{ padding: "9px 11px" }}><div className="k">Lead</div><div className="v" style={{ fontSize: 19 }}>{d.kpis.leads}</div></div>
          <div className="kpi" style={{ padding: "9px 11px" }}><div className="k">Campionature</div><div className="v" style={{ fontSize: 19 }}>{d.kpis.samples}</div></div>
          <div className="kpi" style={{ padding: "9px 11px" }}><div className="k">Ordini</div><div className="v" style={{ fontSize: 19 }}>{d.kpis.orders}</div></div>
          <div className="kpi" style={{ padding: "9px 11px" }}><div className="k">Fatturato</div><div className="v" style={{ fontSize: 19 }}>{moneyCompact(d.kpis.revenue)}</div></div>
          <div className="kpi" style={{ padding: "9px 11px" }}><div className="k">Issue</div><div className="v" style={{ fontSize: 19, color: d.kpis.issues > 0 ? "var(--warn)" : "var(--ink)" }}>{d.kpis.issues}</div></div>
        </div>

        <DossierTabs dossier={d} bundle={bundle} />
      </main>
    </div>
  );
}
