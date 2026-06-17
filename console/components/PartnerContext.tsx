// PartnerContext — intestazione relazione: chi è, hotness/NBA, revenue, conteggi.
// Compare in inbox (risolto dal mittente), lead, card pipeline, dossier, contatto.
import type { PartnerBundle } from "@/lib/types";
import { operatorColor, operatorLabel } from "@/lib/theme";
import { EmptyHonest, money, orHonest } from "./Honest";

export function PartnerContext({ bundle }: { bundle: PartnerBundle }) {
  const { partner, signals, revenue, leads, dossiers, mailThread } = bundle;
  const tierClass =
    signals.hotnessTier === "hot" ? "chip-hot" : signals.hotnessTier === "warm" ? "chip-warm" : "chip-cold";

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{partner.name}</div>
          <div style={{ color: "var(--muted)", fontSize: 13 }}>
            {orHonest(partner.email, "email non disponibile")}
            {partner.city || partner.country ? ` · ${[partner.city, partner.country].filter(Boolean).join(", ")}` : ""}
          </div>
        </div>
        {signals.hotnessTier ? (
          <span className={`chip ${tierClass}`}>
            {signals.hotnessTier}{signals.hotnessScore != null ? ` ${signals.hotnessScore}` : ""}
          </span>
        ) : null}
      </div>

      {/* Next Best Action: SUGGERIMENTO, non invio automatico */}
      <div style={{ marginTop: 10 }}>
        {signals.nbaText ? (
          <div className="empty-honest" style={{ borderStyle: "solid" }}>
            <span><strong>Prossima azione:</strong> {signals.nbaText}</span>
          </div>
        ) : (
          <EmptyHonest label="Nessun suggerimento attivo per questo contatto." />
        )}
      </div>

      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <Stat label="Revenue" value={money(revenue.total, revenue.currency)} />
        <Stat label="Ordini" value={String(revenue.orderCount)} />
        <Stat label="Lead" value={String(leads.length)} />
        <Stat label="Dossier" value={String(dossiers.length)} />
        <Stat label="Mail" value={String(mailThread.length)} />
        <Stat label="Non lette" value={String(signals.unreadMail)} />
      </div>

      {/* Operatori coinvolti */}
      <div style={{ marginTop: 10, display: "flex", gap: 12, flexWrap: "wrap" }}>
        {operatorsOf(bundle).map((op) => (
          <span key={op} className="op-badge">
            <span className="op-dot" style={{ background: operatorColor[op] }} />
            {operatorLabel[op]}
          </span>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function operatorsOf(bundle: PartnerBundle) {
  const set = new Set([...bundle.leads.map((l) => l.operator), ...bundle.dossiers.map((d) => d.operator)]);
  return [...set];
}
