// RelationshipTimeline — cronologia unica della relazione: mail + ordini + lead
// + dossier fusi e ordinati per data. Consuma il bundle.
import type { PartnerBundle } from "@/lib/types";
import { EmptyHonest, dateLabel, money } from "./Honest";

interface TLItem { date: string | null; kind: string; text: string; }

export function RelationshipTimeline({ bundle, limit = 12 }: { bundle: PartnerBundle; limit?: number }) {
  const items: TLItem[] = [];

  for (const m of bundle.mailThread) {
    items.push({
      date: m.date, kind: m.direction === "inbound" ? "Mail ricevuta" : "Mail inviata",
      text: m.subject || "(senza oggetto)",
    });
  }
  for (const o of bundle.orders) {
    items.push({
      date: o.dateOrder, kind: o.isSample ? "Campionatura" : "Ordine",
      text: `${o.name} · ${o.isSample ? "campioni" : money(o.amountTotal, bundle.revenue.currency)}`,
    });
  }
  for (const l of bundle.leads) {
    items.push({ date: l.nextFollowup, kind: "Lead", text: `${l.name}${l.stage ? ` · ${l.stage}` : ""}` });
  }

  const sorted = items
    .map((i) => ({ ...i, t: i.date ? new Date(i.date).getTime() : 0 }))
    .sort((a, b) => b.t - a.t)
    .slice(0, limit);

  return (
    <div className="card">
      <p className="section-title">Timeline relazione</p>
      {sorted.length === 0 ? (
        <EmptyHonest label="Nessuna attività registrata con questo contatto." actionLabel="Crea lead" />
      ) : (
        <div>
          {sorted.map((i, idx) => (
            <div key={idx} className="tl-item">
              <span className="tl-dot" />
              <div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>
                  {dateLabel(i.date)} · {i.kind}
                </div>
                <div>{i.text}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
