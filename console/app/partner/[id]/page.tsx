// Dossier cliente — vista unica (Brief Regia+Dossier). Sostituisce il Dossier v2 a 3 livelli.
// Server: account/library/templates operatore (per le 4 azioni). Header/metriche/timeline sono
// caricati dal client (DossierClient) via i metodi gated console_partner_dossier/_timeline.
import Link from "next/link";
import { auth } from "@/lib/auth";
import { getOperatorAccounts, getLibrary, getTemplates } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { DossierClient } from "@/components/DossierClient";

export const dynamic = "force-dynamic";

export default async function DossierCliente({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth();
  const [accounts, library, templates] = await Promise.all([
    session?.operatorUid ? getOperatorAccounts({ operatorUid: session.operatorUid }) : Promise.resolve([]),
    getLibrary(),
    getTemplates(),
  ]);

  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div><Link href="/" className="muted" style={{ fontSize: 12 }}>← Regia</Link></div>
        <DossierClient partnerId={Number(id)} accounts={accounts} library={library} templates={templates} />
      </main>
    </div>
  );
}
