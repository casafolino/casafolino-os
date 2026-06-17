// Follow-up — 4 colonne (scaduti/oggi, 7 giorni, da pianificare, clienti caldi).
import Link from "next/link";
import { getFollowup } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest, moneyCompact } from "@/components/Honest";
import { operatorColor } from "@/lib/theme";
import type { Tone } from "@/lib/types";

export const dynamic = "force-dynamic";

function dotColor(t: Tone): string {
  return t === "danger" ? "var(--danger)" : t === "warn" ? "var(--warn)" : t === "ok" ? "var(--ok)" : "var(--muted)";
}

export default async function FollowUp() {
  const f = await getFollowup();
  return (
    <div className="app">
      <Sidebar active="followup" variant="rail" />
      <main className="main" style={{ display: "flex", gap: 11 }}>
        {f.columns.length === 0 ? (
          <EmptyHonest label="Nessun follow-up da gestire." actionLabel="Apri pipeline" />
        ) : (
          f.columns.map((col) => (
            <div key={col.key} className="grow">
              <div className="row" style={{ gap: 7, marginBottom: 9 }}>
                <span className="opdot" style={{ background: dotColor(col.tone) }} />
                <span style={{ fontWeight: 600, fontSize: 13 }}>{col.label}</span>
                <span className="muted" style={{ fontSize: 11, marginLeft: "auto" }}>{col.items.length}</span>
              </div>
              {col.items.length === 0 ? (
                <div className="muted" style={{ fontSize: 12 }}>niente qui</div>
              ) : (
                col.items.map((it) => {
                  const card = (
                    <div className="card" style={{ borderLeft: `3px solid ${operatorColor[it.operator]}`, padding: 10, marginBottom: 8 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{it.name}</div>
                      <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>{it.sub}</div>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{it.value != null ? moneyCompact(it.value) : "valore da stimare"}</span>
                        <span className="muted" style={{ fontSize: 11 }}>{it.dateLabel}</span>
                      </div>
                    </div>
                  );
                  return it.partnerId
                    ? <Link key={it.id} href={`/partner/${it.partnerId}`} style={{ display: "block" }}>{card}</Link>
                    : <div key={it.id}>{card}</div>;
                })
              )}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
