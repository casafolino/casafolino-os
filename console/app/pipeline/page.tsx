// Pipeline kanban (schermo 3 di console_reference_v4): colonne, card bordo-sinistro per operatore.
import { getPipeline } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { Icon } from "@/components/Icons";
import { EmptyHonest, moneyCompact } from "@/components/Honest";
import { operatorColor, operatorTint } from "@/lib/theme";
import type { Tone, PipelineCard } from "@/lib/types";

export const dynamic = "force-dynamic";

function badgeStyle(tone: Tone): React.CSSProperties {
  switch (tone) {
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}

function Card({ c }: { c: PipelineCard }) {
  return (
    <div className="card" style={{ borderLeft: `3px solid ${operatorColor[c.operator]}`, padding: 10, marginBottom: 8 }}>
      <div style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</div>
      <div className="muted" style={{ fontSize: 11, marginBottom: 7 }}>{c.sub}</div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span style={{ fontWeight: 600, fontSize: 12 }}>{c.value != null ? moneyCompact(c.value) : "valore da stimare"}</span>
        {c.score != null ? (
          <span className="chip" style={{ background: operatorTint[c.operator], color: operatorColor[c.operator] }}>{c.score}</span>
        ) : null}
      </div>
      {c.badgeLabel ? (
        <div style={{ marginTop: 7 }}>
          <span className="chip" style={badgeStyle(c.badgeTone)}>
            {c.badgeTone === "danger" ? <Icon name="clock" size={11} /> : c.badgeTone === "ok" ? <Icon name="check" size={11} /> : null}
            {c.badgeLabel}
          </span>
        </div>
      ) : null}
    </div>
  );
}

export default async function Pipeline() {
  const p = await getPipeline();

  return (
    <div className="app">
      <Sidebar active="pipeline" variant="rail" />
      <main className="main" style={{ display: "flex", gap: 11 }}>
        {p.columns.length === 0 ? (
          <EmptyHonest label="Nessun lead in pipeline." actionLabel="Crea lead" />
        ) : (
          p.columns.map((col) => (
            <div key={col.key} className="grow">
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 9 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: col.won ? "var(--ok)" : "var(--ink)" }}>{col.label}</span>
                <span className="muted" style={{ fontSize: 11 }}>{col.count}</span>
              </div>
              {col.cards.length === 0 ? (
                <div className="muted" style={{ fontSize: 12 }}>colonna vuota</div>
              ) : (
                col.cards.map((c) => <Card key={c.id} c={c} />)
              )}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
