// Dettaglio mail (read-only): corpo + box contesto del partner risolto.
// sender → dossier (/partner/[id]). Nessun bottone azione.
import Link from "next/link";
import { getMailMessage, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest, dateLabel, moneyCompact } from "@/components/Honest";
import { operatorColor, operatorLabel } from "@/lib/theme";

export const dynamic = "force-dynamic";

export default async function MailDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const m = await getMailMessage(Number(id));
  const bundle = m?.partnerId ? await getPartnerBundle(m.partnerId) : null;
  const lead = bundle?.leads[0] ?? null;

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

            {/* box contesto: Azienda / Owner / Pipeline */}
            {bundle ? (
              <div className="card" style={{ padding: "14px 16px" }}>
                <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                  <div style={{ fontWeight: 600 }}>
                    <Link href={`/partner/${bundle.partner.id}`} style={{ color: "var(--accent)" }}>{bundle.partner.name} →</Link>
                  </div>
                  <span className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)" }}>collegato</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                  <Ctx label="Azienda" value={bundle.partner.name} />
                  <Ctx label="Owner" value={lead ? operatorLabel[lead.operator] : null} empty="non assegnato" color={lead ? operatorColor[lead.operator] : undefined} />
                  <Ctx label="Pipeline" value={lead ? `${lead.stage ?? "senza stage"}${lead.expectedRevenue != null ? ` · ${moneyCompact(lead.expectedRevenue)}` : ""}` : null} empty="nessun lead" />
                </div>
              </div>
            ) : (
              <div className="card" style={{ padding: "14px 16px" }}>
                <div className="empty-honest">
                  <span>Mittente <b>{m.senderEmail || m.senderName}</b> non collegato a nessun partner.</span>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function Ctx({ label, value, empty, color }: { label: string; value: string | null; empty?: string; color?: string }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      {value
        ? <div className="row" style={{ gap: 6, fontWeight: 600, fontSize: 13 }}>
            {color ? <span className="opdot" style={{ background: color }} /> : null}{value}
          </div>
        : <div style={{ fontSize: 12, color: "var(--muted)" }}>{empty ?? "non disponibile"}</div>}
    </div>
  );
}
