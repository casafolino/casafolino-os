// Scheda lead ricca — route dedicata /console/lead/[id]. Server component: risolve gli account
// dell'operatore (per il Composer) dalla sessione, poi delega al client che carica lead+timeline
// via gateway audited (operator_uid server-side).
import Link from "next/link";
import { auth } from "@/lib/auth";
import { getOperatorAccounts } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { LeadCardClient } from "@/components/LeadCardClient";

export const dynamic = "force-dynamic";

export default async function LeadCardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth();
  const accounts = session?.operatorUid
    ? await getOperatorAccounts({ operatorUid: session.operatorUid })
    : [];

  return (
    <div className="app">
      <Sidebar active="pipeline" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div><Link href="/pipeline" className="muted" style={{ fontSize: 12 }}>← Pipeline</Link></div>
        <LeadCardClient leadId={Number(id)} accounts={accounts} />
      </main>
    </div>
  );
}
