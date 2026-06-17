// Home demo (mock) — prova "mail ovunque": lo STESSO thread di Klaus Berger
// compare in Contatto, Lead e Dossier perché tutti consumano getPartnerBundle.
import { getPartnerBundle } from "@/lib/bundle";
import { PartnerContext } from "@/components/PartnerContext";
import { PartnerMailThread } from "@/components/PartnerMailThread";
import { RelationshipTimeline } from "@/components/RelationshipTimeline";
import { EmptyHonest } from "@/components/Honest";

export const dynamic = "force-dynamic"; // legge il bundle a ogni richiesta

export default async function Home() {
  const klaus = await getPartnerBundle(9001);
  const neumann = await getPartnerBundle(9002);

  return (
    <div className="shell">
      <nav className="shell-nav">
        <div style={{ fontWeight: 800, marginBottom: 16 }}>CasaFolino</div>
        <a href="#">Regia</a>
        <a href="#">Inbox</a>
        <a href="#">Pipeline</a>
        <a href="#">Dossier</a>
        <a href="#">Follow-up</a>
        <a href="#">Fiere</a>
        <div style={{ marginTop: 20, fontSize: 11, opacity: 0.7 }}>
          fonte dati: {klaus?.source ?? "non disponibile"}
        </div>
      </nav>

      <main className="shell-main">
        <h2 style={{ marginTop: 0 }}>Foundation demo · relazione per partner</h2>

        {!klaus ? (
          <EmptyHonest label="Bundle Klaus non disponibile." />
        ) : (
          <>
            <PartnerContext bundle={klaus} />

            <div className="grid-2" style={{ marginTop: 16 }}>
              {/* Stesso thread nel contesto LEAD */}
              <div>
                <p className="section-title">Vista Lead — {klaus.leads[0]?.name ?? "nessun lead"}</p>
                <PartnerMailThread messages={klaus.mailThread} title="Mail (nel lead)" limit={5} />
              </div>
              {/* Stesso thread nel contesto DOSSIER */}
              <div>
                <p className="section-title">Vista Dossier — {klaus.dossiers[0]?.name ?? "nessun dossier"}</p>
                <PartnerMailThread messages={klaus.mailThread} title="Mail (nel dossier)" limit={5} />
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <RelationshipTimeline bundle={klaus} />
            </div>
          </>
        )}

        {/* Inbox: contesto risolto dal mittente anche SENZA lead collegato */}
        <h3 style={{ marginTop: 24 }}>Inbox — contesto dal mittente (senza lead)</h3>
        {neumann ? <PartnerContext bundle={neumann} /> : <EmptyHonest label="Nessun contatto risolto." actionLabel="Crea contatto" />}
      </main>
    </div>
  );
}
