// Hub partner — centro della navigazione circolare: da qui a lead/dossier/ordini/mail e ritorno.
import Link from "next/link";
import { getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { PartnerContext } from "@/components/PartnerContext";
import { PartnerMailThread } from "@/components/PartnerMailThread";
import { RelationshipTimeline } from "@/components/RelationshipTimeline";
import { EmptyHonest, money, moneyCompact, dateLabel } from "@/components/Honest";
import { operatorColor } from "@/lib/theme";
import { CampionaturaButton } from "@/components/CampionaturaButton";

export const dynamic = "force-dynamic";

export default async function PartnerHub({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bundle = await getPartnerBundle(Number(id));

  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main">
        <div className="row" style={{ marginBottom: 12, justifyContent: "space-between", alignItems: "center" }}>
          <Link href="/inbox" className="muted" style={{ fontSize: 12 }}>← Inbox</Link>
          {bundle ? <CampionaturaButton partnerId={bundle.partner.id} leadId={bundle.leads[0]?.id ?? null} small label="Campionatura" /> : null}
        </div>
        {!bundle ? (
          <EmptyHonest label="Partner non trovato." actionLabel="Torna all'inbox" />
        ) : (
          <>
            <PartnerContext bundle={bundle} />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
              {/* Lead → dossier collegato */}
              <div className="card">
                <p className="sec-title">Lead · {bundle.leads.length}</p>
                {bundle.leads.length === 0 ? <EmptyHonest label="Nessun lead." actionLabel="Crea lead" /> : (
                  bundle.leads.map((l) => (
                    <Link key={l.id} href={`/lead/${l.id}`} style={{ display: "block" }}>
                      <div className="card" style={{ borderLeft: `3px solid ${operatorColor[l.operator]}`, padding: 10, marginBottom: 8 }}>
                        <div className="row" style={{ justifyContent: "space-between" }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{l.name}</span>
                          <span className="muted" style={{ fontSize: 12 }}>{l.expectedRevenue != null ? moneyCompact(l.expectedRevenue) : "da stimare"}</span>
                        </div>
                        <div className="muted" style={{ fontSize: 11 }}>{l.stage ?? "senza stage"} · score {l.score ?? "n/d"} · apri scheda →</div>
                      </div>
                    </Link>
                  ))
                )}
              </div>

              {/* Dossier → pagina dossier */}
              <div className="card">
                <p className="sec-title">Dossier · {bundle.dossiers.length}</p>
                {bundle.dossiers.length === 0 ? <EmptyHonest label="Nessun dossier." actionLabel="Promuovi a dossier" /> : (
                  bundle.dossiers.map((d) => (
                    <Link key={d.id} href="/dossier" style={{ display: "block" }}>
                      <div className="card" style={{ borderLeft: `3px solid ${operatorColor[d.operator]}`, padding: 10, marginBottom: 8 }}>
                        <div style={{ fontWeight: 600, fontSize: 13, color: "var(--accent)" }}>{d.name} →</div>
                        <div className="muted" style={{ fontSize: 11 }}>{d.status ?? ""} · {d.valueEstimate != null ? moneyCompact(d.valueEstimate) : "valore da stimare"}</div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
              <PartnerMailThread messages={bundle.mailThread} title="Mail con questo partner" limit={6} />
              <div>
                <div className="card" style={{ marginBottom: 16 }}>
                  <p className="sec-title">Ordini · {bundle.orders.length}</p>
                  {bundle.orders.length === 0 ? <EmptyHonest label="Nessun ordine." /> : (
                    bundle.orders.map((o) => (
                      <div key={o.id} className="row" style={{ justifyContent: "space-between", padding: "4px 0", fontSize: 13 }}>
                        <span>{o.name}{o.isSample ? " · campioni" : ""}</span>
                        <span className="muted">{dateLabel(o.dateOrder)} · {money(o.amountTotal, bundle.revenue.currency)}</span>
                      </div>
                    ))
                  )}
                </div>
                <RelationshipTimeline bundle={bundle} limit={8} />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
