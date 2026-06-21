"use client";
// Timeline attività del lead: voci tipizzate (mail / campionatura / nota) con icona+colore.
// Le mail del console emergono qui (sorgente partner+lead_id). Empty state onesto.
// La campionatura in corso mostra il semaforo (riusa CampionaturaTimeline).
import { dateLabel } from "@/components/Honest";
import { CampionaturaTimeline } from "@/components/CampionaturaTimeline";
import { timelineMeta, type LeadTimelineItem } from "@/lib/lead";

export function LeadTimeline({ items, activeShipmentId }: { items: LeadTimelineItem[]; activeShipmentId?: number }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <p className="sec-title">Timeline attività</p>

      {activeShipmentId ? (
        <div style={{ marginBottom: 12 }}>
          <CampionaturaTimeline shipmentId={activeShipmentId} compact />
        </div>
      ) : null}

      {items.length === 0 ? (
        <div className="empty-honest">Nessuna mail collegata a questo lead.</div>
      ) : (
        <div>
          {items.map((i, idx) => {
            const meta = timelineMeta[i.type];
            return (
              <div key={idx} className="tl-item" style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ width: 22, height: 22, borderRadius: 11, flexShrink: 0,
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                  background: "var(--panel-2)", fontSize: 12 }}>{meta.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    {dateLabel(i.date)} · <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
                    {i.direction ? ` · ${i.direction === "inbound" ? "ricevuta" : "inviata"}` : ""}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{i.title}</div>
                  {i.subtitle ? <div className="muted" style={{ fontSize: 12 }}>{i.subtitle}</div> : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
