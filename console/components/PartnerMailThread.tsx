// PartnerMailThread — "mail ovunque": stesso thread del bundle in contatto,
// lead, card pipeline, dossier. Riceve i messaggi dal bundle (un'unica fonte).
import type { MailMessage } from "@/lib/types";
import { EmptyHonest, dateLabel } from "./Honest";

export function PartnerMailThread({
  messages,
  title = "Mail",
  limit,
}: {
  messages: MailMessage[];
  title?: string;
  limit?: number;
}) {
  const list = limit ? messages.slice(0, limit) : messages;
  return (
    <div className="card">
      <p className="section-title">{title} · {messages.length}</p>
      {list.length === 0 ? (
        <EmptyHonest label="Nessuna mail con questo contatto." actionLabel="Scrivi la prima" />
      ) : (
        <div>
          {list.map((m) => (
            <div key={m.id} className={`mail-item ${m.direction === "inbound" ? "mail-dir-in" : "mail-dir-out"}`}>
              <div className="mail-meta">
                <span className={!m.isRead && m.direction === "inbound" ? "mail-unread" : ""}>
                  {m.direction === "inbound" ? "← " : "→ "}
                  {m.senderName || m.senderEmail || "mittente sconosciuto"}
                  {m.matchType === "domain" ? <span className="chip" style={{ marginLeft: 6 }}>dominio</span> : null}
                </span>
                <span>{dateLabel(m.date)}</span>
              </div>
              <div className={!m.isRead && m.direction === "inbound" ? "mail-unread" : ""}>
                {m.subject || "(senza oggetto)"}
              </div>
              {m.snippet ? <div style={{ color: "var(--muted)", fontSize: 13 }}>{m.snippet}</div> : null}
              {m.aiUrgency === "high" ? <span className="chip chip-hot" style={{ marginTop: 4 }}>urgenza alta</span> : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
