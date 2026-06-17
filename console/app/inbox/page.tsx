// Inbox 3-pane (schermo 2 di console_reference_v4): rail + lista + corpo + contesto dal mittente.
import { getInbox, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { Icon } from "@/components/Icons";
import { PartnerMailThread } from "@/components/PartnerMailThread";
import { AiDraftButton } from "@/components/AiDraftButton";
import { CreateLeadButton } from "@/components/CreateLeadButton";
import { EmptyHonest, money, moneyCompact, dateLabel } from "@/components/Honest";
import { operatorColor } from "@/lib/theme";
import type { Tone } from "@/lib/types";

export const dynamic = "force-dynamic";

function toneStyle(tone: Tone): React.CSSProperties {
  switch (tone) {
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}

function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

export default async function Inbox() {
  const inbox = await getInbox();
  const bundle = inbox.selectedPartnerId ? await getPartnerBundle(inbox.selectedPartnerId) : null;
  const m = inbox.message;

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />

      {/* Pane 2: lista */}
      <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid var(--line)", background: "var(--paper)" }}>
        <div style={{ padding: "11px 13px", borderBottom: "1px solid var(--line)", fontWeight: 600 }}>Inbox</div>
        {inbox.items.map((it) => {
          const selected = it.id === inbox.selectedId;
          return (
            <div key={it.id} style={{
              padding: "10px 13px",
              borderLeft: `3px solid ${selected ? "var(--accent)" : "transparent"}`,
              background: selected ? "var(--accent-t)" : "transparent",
            }}>
              <div className="row" style={{ gap: 6 }}>
                <span className="opdot" style={{ background: operatorColor[it.operator] }} />
                <span style={{ fontWeight: 600, fontSize: 13 }}>{it.name}</span>
              </div>
              <div className="muted" style={{ fontSize: 11, margin: "2px 0 5px" }}>{it.org}</div>
              {it.badgeLabel ? <span className="chip" style={toneStyle(it.badgeTone)}>{it.badgeLabel}</span> : null}
            </div>
          );
        })}
      </div>

      {/* Pane 3: corpo + contesto */}
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Messaggio aperto */}
        <div className="card" style={{ padding: "14px 16px" }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.subject || "(senza oggetto)"}</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 11 }}>
            <span style={{ color: "var(--ink)", fontWeight: 600 }}>{m.senderName}</span> · {m.senderEmail} · {m.timeLabel}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 13 }}>{m.body}</div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <span className="btn pri"><Icon name="reply" size={14} /> Rispondi · F8</span>
            <AiDraftButton subject={m.subject} body={m.body} partnerName={m.senderName} to={m.senderEmail} />
            <span className="btn"><Icon name="link" size={14} /> Collega</span>
          </div>
        </div>

        {/* Contesto dal mittente (NON dal lead) */}
        {bundle ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--ok-t)", color: "var(--ok)",
                display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, flexShrink: 0 }}>
                {initials(bundle.partner.name)}
              </div>
              <div className="grow">
                <div style={{ fontWeight: 600 }}>
                  {bundle.partner.name}
                  {bundle.partner.role || bundle.partner.country ? (
                    <span className="chip" style={{ marginLeft: 4 }}>
                      {[bundle.partner.role, bundle.partner.country].filter(Boolean).join(" · ")}
                    </span>
                  ) : null}
                </div>
                <div className="muted" style={{ fontSize: 11 }}>
                  <Icon name="check" size={13} color="var(--ok)" /> riconosciuto dal mittente · match{" "}
                  {inbox.resolutionMatch === "domain" ? "dominio " : inbox.resolutionMatch === "exact" ? "esatto " : ""}
                  <span style={{ fontFamily: "var(--mono)" }}>{bundle.partner.domain ?? bundle.partner.email}</span>
                </div>
              </div>
            </div>

            {/* 2x2: Lead / Dossier / Ultimo ordine / Fatturato */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              <CtxCell label="Lead" value={bundle.leads[0] ? `${bundle.leads[0].stage ?? "lead"} · score ${bundle.leads[0].score ?? "n/d"}` : null} empty="Nessun lead" accent={false} />
              <CtxCell label="Dossier" value={bundle.dossiers[0] ? `${bundle.dossiers[0].name} · ${bundle.dossiers[0].status ?? ""}` : null} empty="Nessun dossier" accent />
              <CtxCell label="Ultimo ordine" value={lastOrder(bundle)} empty="Nessun ordine" accent={false} />
              <CtxCell label="Fatturato" value={bundle.revenue.total > 0 ? moneyCompact(bundle.revenue.total) : null} empty="Nessun fatturato" accent={false} />
            </div>

            {/* Prossima azione (suggerimento) */}
            {bundle.signals.nbaText ? (
              <div className="row" style={{ gap: 8, background: "var(--warn-t)", padding: "8px 11px", borderRadius: "var(--r-md)", marginBottom: 12 }}>
                <Icon name="alert" size={16} color="var(--warn)" />
                <span className="grow" style={{ fontSize: 12, color: "#6B4A12" }}><b>Prossima azione:</b> {bundle.signals.nbaText}</span>
              </div>
            ) : null}

            {/* MAIL OVUNQUE: stesso thread del bundle, sempre visibile */}
            <PartnerMailThread messages={bundle.mailThread} title="Mail con questo partner (qui, nel lead, nel dossier)" limit={5} />
          </div>
        ) : (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest">
              <span>Mittente non riconosciuto: nessun partner collegato.</span>
              <CreateLeadButton name={`Nuovo contatto · ${m.senderName || m.senderEmail}`} emailFrom={m.senderEmail} />
            </div>
            <div style={{ marginTop: 10 }}>
              <PartnerMailThread messages={[]} title="Mail con questo partner" />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function CtxCell({ label, value, empty, accent }: { label: string; value: string | null; empty: string; accent: boolean }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      {value ? (
        <div style={{ fontWeight: 600, fontSize: 13, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}</div>
      ) : (
        <div style={{ fontSize: 12, color: "var(--muted)" }}>{empty}</div>
      )}
    </div>
  );
}

function lastOrder(bundle: { orders: { isSample: boolean; dateOrder: string | null; amountTotal: number }[]; revenue: { currency: string } }): string | null {
  const real = bundle.orders.filter((o) => !o.isSample);
  if (real.length === 0) return null;
  const o = real[0];
  return `${dateLabel(o.dateOrder)} · ${money(o.amountTotal, bundle.revenue.currency)}`;
}
