// Hub partner — scheda al livello della scheda lead (Brief 19). Server: bundle + account operatore
// (per il Composer), poi delega al client PartnerClient (stesso design system di LeadCardClient).
import Link from "next/link";
import { auth } from "@/lib/auth";
import { getPartnerBundle, getOperatorAccounts } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest } from "@/components/Honest";
import { PartnerClient } from "@/components/PartnerClient";

export const dynamic = "force-dynamic";

export default async function PartnerHub({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth();
  const [bundle, accounts] = await Promise.all([
    getPartnerBundle(Number(id)),
    session?.operatorUid ? getOperatorAccounts({ operatorUid: session.operatorUid }) : Promise.resolve([]),
  ]);

  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div><Link href="/inbox" className="muted" style={{ fontSize: 12 }}>← Inbox</Link></div>
        {!bundle ? (
          <EmptyHonest label="Partner non trovato." actionLabel="Torna all'inbox" />
        ) : (
          <PartnerClient bundle={bundle} accounts={accounts} />
        )}
      </main>
    </div>
  );
}
