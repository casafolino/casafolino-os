"use client";
// S1 — pannello collassabile "Altre mail con questo partner (non assegnate a questa trattativa)".
// Sorgente: console_get_lead_other_mails (partner_id match, lead_id vuoto). Azione per riga:
// "Assegna a questo lead" → scrive lead_id (+ thread-assist server-side) → la mail sparisce di qui
// e compare in timeline (onAssigned refetcha la timeline).
import { useEffect, useState } from "react";
import { dateLabel } from "@/components/Honest";
import { getLeadOtherMails, assignMailToLead, type OtherMail } from "@/lib/lead";

export function LeadOtherMails({ leadId, hasPartner, onAssigned }: {
  leadId: number; hasPartner: boolean; onAssigned: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<OtherMail[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  function load() {
    getLeadOtherMails(leadId)
      .then((r) => { setItems(r?.items ?? []); setLoaded(true); })
      .catch((e) => { setErr((e as Error).message); setLoaded(true); });
  }

  useEffect(() => { if (hasPartner) load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [leadId, hasPartner]);

  if (!hasPartner) return null;
  if (loaded && items.length === 0) return null; // niente storico → niente rumore

  async function assign(m: OtherMail) {
    setBusy(m.id);
    const snapshot = items;
    setItems((cur) => cur.filter((x) => x.id !== m.id)); // ottimistico
    try {
      const r = await assignMailToLead(leadId, m.id);
      if (r.ok) onAssigned(); // la timeline ora include questa mail (+ sorelle del thread)
      else { setItems(snapshot); setErr(r.message ?? "assegnazione negata"); }
    } catch (e) { setItems(snapshot); setErr((e as Error).message); }
    finally { setBusy(null); }
  }

  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={() => setOpen((o) => !o)}>
        <p className="sec-title" style={{ margin: 0 }}>
          {open ? "▾" : "▸"} Altre mail con questo partner
          <span className="muted" style={{ fontWeight: 400 }}> · {items.length} non assegnate</span>
        </p>
      </div>
      {err ? <div className="muted" style={{ fontSize: 12, color: "var(--danger)", marginTop: 6 }}>{err}</div> : null}
      {open ? (
        <div style={{ marginTop: 10 }}>
          {items.map((m) => (
            <div key={m.id} className="row" style={{ justifyContent: "space-between", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>
                  {dateLabel(m.date)}{m.direction ? ` · ${m.direction === "inbound" ? "ricevuta" : "inviata"}` : ""}
                </div>
                <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.title}</div>
                {m.subtitle ? <div className="muted" style={{ fontSize: 12 }}>{m.subtitle}</div> : null}
              </div>
              <button className="btn" disabled={busy === m.id} onClick={() => assign(m)}
                style={{ flexShrink: 0, fontSize: 12, color: "var(--accent)", borderColor: "var(--accent)" }}>
                {busy === m.id ? "…" : "→ Assegna a questo lead"}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
