"use client";
// Inbox 3-pane interattivo: clic sulla lista cambia messaggio + contesto.
import { useState } from "react";
import { Icon } from "./Icons";
import { PartnerMailThread } from "./PartnerMailThread";
import { AiDraftButton } from "./AiDraftButton";
import { CreateLeadButton } from "./CreateLeadButton";
import { LinkLeadButton } from "./LinkLeadButton";
import { money, moneyCompact, dateLabel } from "./Honest";
import { operatorColor } from "@/lib/theme";
import type { InboxItem, PartnerBundle, Tone } from "@/lib/types";

function toneStyle(t: Tone): React.CSSProperties {
  switch (t) {
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}
function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

export function InboxClient({ items, bundles, initialSelectedId }: { items: InboxItem[]; bundles: Record<number, PartnerBundle>; initialSelectedId: number }) {
  const [selectedId, setSelectedId] = useState(initialSelectedId);
  const item = items.find((i) => i.id === selectedId) ?? items[0];
  const bundle = item?.partnerId ? bundles[item.partnerId] : null;
  const m = item?.message;

  return (
    <>
      {/* Pane 2: lista */}
      <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid var(--line)", background: "var(--paper)" }}>
        <div style={{ padding: "11px 13px", borderBottom: "1px solid var(--line)", fontWeight: 600 }}>Inbox</div>
        {items.map((it) => {
          const sel = it.id === selectedId;
          return (
            <div key={it.id} onClick={() => setSelectedId(it.id)} style={{
              padding: "10px 13px", cursor: "pointer",
              borderLeft: `3px solid ${sel ? "var(--accent)" : "transparent"}`,
              background: sel ? "var(--accent-t)" : "transparent",
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
        <div className="card" style={{ padding: "14px 16px" }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{m?.subject || "(senza oggetto)"}</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 11 }}>
            <span style={{ color: "var(--ink)", fontWeight: 600 }}>{m?.senderName}</span> · {m?.senderEmail} · {m?.timeLabel}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 13 }}>{m?.body}</div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <span className="btn pri"><Icon name="reply" size={14} /> Rispondi · F8</span>
            {m ? <AiDraftButton subject={m.subject} body={m.body} partnerName={m.senderName} to={m.senderEmail} /> : null}
            <LinkLeadButton messageId={item.id} leadId={bundle?.leads[0]?.id ?? null} leadName={bundle?.leads[0]?.name} />
          </div>
        </div>

        {bundle ? (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--ok-t)", color: "var(--ok)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, flexShrink: 0 }}>{initials(bundle.partner.name)}</div>
              <div className="grow">
                <div style={{ fontWeight: 600 }}>
                  {bundle.partner.name}
                  {bundle.partner.role || bundle.partner.country ? <span className="chip" style={{ marginLeft: 4 }}>{[bundle.partner.role, bundle.partner.country].filter(Boolean).join(" · ")}</span> : null}
                </div>
                <div className="muted" style={{ fontSize: 11 }}>
                  <Icon name="check" size={13} color="var(--ok)" /> riconosciuto dal mittente · match {item.resolutionMatch === "domain" ? "dominio " : item.resolutionMatch === "exact" ? "esatto " : ""}
                  <span style={{ fontFamily: "var(--mono)" }}>{bundle.partner.domain ?? bundle.partner.email}</span>
                </div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              <Cell label="Lead" value={bundle.leads[0] ? `${bundle.leads[0].stage ?? "lead"} · score ${bundle.leads[0].score ?? "n/d"}` : null} empty="Nessun lead" accent={false} />
              <Cell label="Dossier" value={bundle.dossiers[0] ? `${bundle.dossiers[0].name} · ${bundle.dossiers[0].status ?? ""}` : null} empty="Nessun dossier" accent />
              <Cell label="Ultimo ordine" value={lastOrder(bundle)} empty="Nessun ordine" accent={false} />
              <Cell label="Fatturato" value={bundle.revenue.total > 0 ? moneyCompact(bundle.revenue.total) : null} empty="Nessun fatturato" accent={false} />
            </div>
            {bundle.signals.nbaText ? (
              <div className="row" style={{ gap: 8, background: "var(--warn-t)", padding: "8px 11px", borderRadius: "var(--r-md)", marginBottom: 12 }}>
                <Icon name="alert" size={16} color="var(--warn)" />
                <span className="grow" style={{ fontSize: 12, color: "#6B4A12" }}><b>Prossima azione:</b> {bundle.signals.nbaText}</span>
              </div>
            ) : null}
            <PartnerMailThread messages={bundle.mailThread} title="Mail con questo partner (qui, nel lead, nel dossier)" limit={5} />
          </div>
        ) : (
          <div className="card" style={{ padding: "14px 16px" }}>
            <div className="empty-honest">
              <span>Mittente non riconosciuto: nessun partner collegato.</span>
              {m ? <CreateLeadButton name={`Nuovo contatto · ${m.senderName || m.senderEmail}`} emailFrom={m.senderEmail} /> : null}
            </div>
            <div style={{ marginTop: 10 }}><PartnerMailThread messages={[]} title="Mail con questo partner" /></div>
          </div>
        )}
      </main>
    </>
  );
}

function Cell({ label, value, empty, accent }: { label: string; value: string | null; empty: string; accent: boolean }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      {value ? <div style={{ fontWeight: 600, fontSize: 13, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}</div>
             : <div style={{ fontSize: 12, color: "var(--muted)" }}>{empty}</div>}
    </div>
  );
}
function lastOrder(bundle: PartnerBundle): string | null {
  const real = bundle.orders.filter((o) => !o.isSample);
  if (real.length === 0) return null;
  return `${dateLabel(real[0].dateOrder)} · ${money(real[0].amountTotal, bundle.revenue.currency)}`;
}
