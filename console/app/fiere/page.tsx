// Fiere — elenco fiere con stato e KPI (lead, fatturato generato).
import { getFiere } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest, moneyCompact } from "@/components/Honest";
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

export default async function Fiere() {
  const f = await getFiere();
  return (
    <div className="app">
      <Sidebar active="fiere" variant="rail" />
      <main className="main">
        <h2 style={{ fontSize: 19, marginBottom: 14 }}>Fiere</h2>
        {f.fairs.length === 0 ? (
          <EmptyHonest label="Nessuna fiera registrata." actionLabel="Nuova fiera" />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            {f.fairs.map((fair) => (
              <div key={fair.id} className="card" style={{ padding: "14px 16px" }}>
                <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontWeight: 600 }}>{fair.name}</span>
                  <span className="chip" style={tone(fair.statusTone)}>{fair.status}</span>
                </div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{fair.location} · {fair.dateLabel}</div>
                <div className="row" style={{ gap: 18 }}>
                  <div>
                    <div className="muted" style={{ fontSize: 11 }}>Lead</div>
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{fair.leads > 0 ? fair.leads : "nessuno ancora"}</div>
                  </div>
                  <div>
                    <div className="muted" style={{ fontSize: 11 }}>Fatturato</div>
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{fair.revenue > 0 ? moneyCompact(fair.revenue) : "da generare"}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
