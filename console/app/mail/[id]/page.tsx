// Dettaglio mail (read-only): corpo + cruscotto relazione (Brief 15).
// Il cruscotto risolve il mittente per email (partner/lead/dossier) + create rapidi (Apri/Crea).
import Link from "next/link";
import { getMailMessage } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest, dateLabel } from "@/components/Honest";
import { operatorColor } from "@/lib/theme";
import { MailCockpit } from "@/components/MailCockpit";

export const dynamic = "force-dynamic";

export default async function MailDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const m = await getMailMessage(Number(id));

  return (
    <div className="app">
      <Sidebar active="mail" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div><Link href="/mail" className="muted" style={{ fontSize: 12 }}>← Mail</Link></div>

        {!m ? (
          <EmptyHonest label="Messaggio non trovato." />
        ) : (
          <>
            {/* corpo mail */}
            <div className="card" style={{ padding: "14px 16px" }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.subject}</div>
              <div className="muted" style={{ fontSize: 12, marginBottom: 11 }}>
                <span className="opdot" style={{ background: operatorColor[m.operator], marginRight: 6 }} />
                <span style={{ color: "var(--ink)", fontWeight: 600 }}>{m.senderName || m.senderEmail}</span>
                {m.senderEmail ? ` · ${m.senderEmail}` : ""} · {dateLabel(m.date)} · casella {m.accountName}
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                {m.body || <span className="muted">Nessun corpo testuale disponibile.</span>}
              </div>
            </div>

            {/* cruscotto relazione + create rapidi */}
            <MailCockpit mailId={Number(id)} />
          </>
        )}
      </main>
    </div>
  );
}
