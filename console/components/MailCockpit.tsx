"use client";
// Brief 15 — cruscotto mail: stato relazione del mittente (cliente/pipeline/dossier) a colpo
// d'occhio + barra create rapidi. Esiste → "Apri", altrimenti → "Crea" (niente duplicati).
// Riusa i wizard B8/B9. Manager-only (gateway).
import { useEffect, useState } from "react";
import Link from "next/link";
import { getMailCockpit, type CockpitData } from "@/lib/cockpit";
import { CreateContactButton } from "@/components/CreateContactButton";
import { QuickCreateLead, QuickCreateDossier, QuickCreateCompany } from "@/components/QuickCreate";
import { CampionaturaButton } from "@/components/CampionaturaButton";

export function MailCockpit({ mailId }: { mailId: number }) {
  const [c, setC] = useState<CockpitData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getMailCockpit(mailId).then((d) => { if (d && d.sender) setC(d); else setErr(d?.message ?? "errore"); }).catch((e) => setErr((e as Error).message));
  }, [mailId]);

  if (err) return <div className="card" style={{ padding: 14, color: "var(--danger)" }}>Errore cruscotto: {err}</div>;
  if (!c) return <div className="card muted" style={{ padding: 14 }}>Carico cruscotto…</div>;

  const partnerId = c.partner.exists ? (c.partner.id as number) : null;
  const leadId = c.lead.exists ? (c.lead.id as number) : null;

  return (
    <div className="card" style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* STATO a colpo d'occhio */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        <Status label="Cliente"
          on={c.partner.exists}
          yes={<Link href={`/partner/${c.partner.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{c.partner.name} →</Link>}
          no="Nuovo mittente" />
        <Status label="Pipeline"
          on={c.lead.exists}
          yes={<Link href={`/lead/${c.lead.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{c.lead.stage || "lead"} →</Link>}
          no="Nessun lead" />
        <Status label="Dossier"
          on={c.dossier.exists}
          yes={<span style={{ fontWeight: 600 }}>{c.dossier.name}</span>}
          no="Nessun dossier" />
      </div>

      {/* BARRA CREATE RAPIDI — Apri se esiste, Crea se no */}
      <div className="row" style={{ gap: 8, flexWrap: "wrap", borderTop: "1px solid var(--line)", paddingTop: 10 }}>
        {/* Contatto */}
        {c.partner.exists ? (
          <Link href={`/partner/${c.partner.id}`} className="btn-mini">Apri contatto</Link>
        ) : (
          <CreateContactButton mailId={mailId} />
        )}
        {/* Azienda standalone */}
        {c.company.exists ? (
          <Link href={`/partner/${c.company.id}`} className="btn-mini">Apri azienda</Link>
        ) : (
          <QuickCreateCompany defaultName={c.sender.name} defaultDomain={c.sender.email.split("@")[1] || ""} mailId={mailId} label="Crea azienda" />
        )}
        {/* Lead (con scelta fase) */}
        {c.lead.exists ? (
          <Link href={`/lead/${c.lead.id}`} className="btn-mini">Apri lead</Link>
        ) : (
          <QuickCreateLead partnerId={partnerId} fromMailId={mailId} stages={c.leadStages} label="Crea lead" />
        )}
        {/* Dossier */}
        {c.dossier.exists ? (
          <span className="btn-mini" style={{ opacity: 0.7 }}>Dossier: {c.dossier.name}</span>
        ) : (
          <QuickCreateDossier partnerId={partnerId} leadId={leadId} defaultName={c.partner.exists ? `Dossier ${c.partner.name}` : undefined} label="Crea dossier" />
        )}
        {/* Campionatura (sempre, su partner/lead risolti) */}
        <CampionaturaButton partnerId={partnerId} leadId={leadId} small label="Campionatura" />
      </div>
    </div>
  );
}

function Status({ label, on, yes, no }: { label: string; on: boolean; yes: React.ReactNode; no: string }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 5 }}>
        <span style={{ width: 7, height: 7, borderRadius: 5, background: on ? "var(--ok)" : "var(--line)", display: "inline-block" }} />
        {label}
      </div>
      <div style={{ fontSize: 13, marginTop: 2 }}>{on ? yes : <span className="muted">{no}</span>}</div>
    </div>
  );
}
