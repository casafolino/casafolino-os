// /debug — pagina diagnostica (ex-home foundation): prova "mail ovunque" sul bundle.
import { getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { PartnerContext } from "@/components/PartnerContext";
import { PartnerMailThread } from "@/components/PartnerMailThread";
import { RelationshipTimeline } from "@/components/RelationshipTimeline";
import { EmptyHonest } from "@/components/Honest";

export const dynamic = "force-dynamic";

export default async function Debug() {
  const klaus = await getPartnerBundle(9001);
  const neumann = await getPartnerBundle(9002);

  return (
    <div className="app">
      <Sidebar active="regia" source={klaus ? `${klaus.source} (debug)` : "mock"} />
      <main className="main">
        <h2 style={{ fontSize: 19 }}>Debug · relazione per partner</h2>
        {!klaus ? (
          <EmptyHonest label="Bundle Klaus non disponibile." />
        ) : (
          <>
            <div style={{ marginTop: 12 }}><PartnerContext bundle={klaus} /></div>
            <div className="grid-2" style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <p className="sec-title">Vista Lead, {klaus.leads[0]?.name ?? "nessun lead"}</p>
                <PartnerMailThread messages={klaus.mailThread} title="Mail (nel lead)" limit={5} />
              </div>
              <div>
                <p className="sec-title">Vista Dossier, {klaus.dossiers[0]?.name ?? "nessun dossier"}</p>
                <PartnerMailThread messages={klaus.mailThread} title="Mail (nel dossier)" limit={5} />
              </div>
            </div>
            <div style={{ marginTop: 16 }}><RelationshipTimeline bundle={klaus} /></div>
          </>
        )}
        <h3 className="sec-title" style={{ marginTop: 24 }}>Inbox, contesto dal mittente (senza lead)</h3>
        {neumann ? <PartnerContext bundle={neumann} /> : <EmptyHonest label="Nessun contatto risolto." actionLabel="Crea contatto" />}
      </main>
    </div>
  );
}
