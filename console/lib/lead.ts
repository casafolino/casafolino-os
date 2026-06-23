// Tipi + client helpers per la scheda lead ricca (Brief 4). operator_uid sempre dalla sessione.
import { BP } from "@/lib/basePath";

export type LeadStage = { id: number; name: string; sequence: number; isWon: boolean; isLost: boolean };

export type LeadPartner = {
  id: number; name: string; email: string; phone: string;
  city: string; country: string; isCompany: boolean; role: string;
  function?: string; website?: string; vat?: string; // S3 — arricchimento contatto
};

// S3 — card Azienda arricchita (standard Odoo + Agente 007).
export type LeadCompany = {
  id: number; name: string;
  vat?: string; website?: string; country?: string; city?: string; phone?: string;
  channel?: string; sector?: string; certifications?: string; revenue?: string; employees?: string;
  enriched?: boolean;
};

export type LeadDetail = {
  id: number;
  name: string;
  stageId: number;
  stageName: string;
  stages: LeadStage[];
  ownerUid: number;
  owner: string;
  expectedRevenue: number | null;
  probability: number | null;
  score: number | null;
  rottingState: string | null;
  activityState: string | null; // Brief 20 B — da attività reale
  daysInactive: number | null;
  createDate: string | null;
  daysOpen: number | null;
  nextAction: { date: string | null; summary: string } | null;
  partner: LeadPartner | false;
  company: LeadCompany | false;
  dossier: { id: number; name: string; status: string; valueEstimate: number | null } | false;
  emailFrom: string;
  role?: "manager" | "operator"; // S4 — ruolo del chiamante (whitelist edit differenziata)
  message?: string;
};

// S4 — whitelist campi editabili per ruolo. Il server (console_update_lead) è l'autorità finale;
// qui la UI mostra solo ciò che il ruolo può toccare. CRM è manager-only (Brief 5): l'operatore
// non raggiunge nemmeno la scheda → whitelist ridotta puramente difensiva.
export const LEAD_EDITABLE_BY_ROLE: Record<string, string[]> = {
  manager: ["stage_id", "expected_revenue", "probability", "email_from", "cf_date_next_followup", "name"],
  operator: ["cf_date_next_followup"],
};

export type TimelineKind = "mail" | "campionatura" | "note";
export type LeadTimelineItem = {
  type: TimelineKind;
  date: string | null;
  title: string;
  subtitle: string;
  direction?: "inbound" | "outbound";
  shipmentId?: number;
  messageId?: number; // S1/S2 — mail navigabile (link a /mail/[id])
};
export type LeadTimeline = { leadId: number; items: LeadTimelineItem[]; message?: string };

// S1 — mail storiche del partner NON assegnate a questa trattativa (pannello collassabile).
export type OtherMail = {
  id: number; date: string | null; title: string; subtitle: string;
  direction?: "inbound" | "outbound";
};
export type OtherMails = { leadId: number; partnerId: number | false; items: OtherMail[]; message?: string };
export type AssignMailResult = { ok?: boolean; leadId?: number; assigned?: number[]; count?: number; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getLead = (leadId: number) => post<LeadDetail>("/api/console/lead/get", { leadId });
export const getLeadTimeline = (leadId: number) => post<LeadTimeline>("/api/console/lead/timeline", { leadId });

// S1 — pannello "Altre mail con questo partner" + assegnazione (thread-assist server-side).
export const getLeadOtherMails = (leadId: number) => post<OtherMails>("/api/console/lead/other-mails", { leadId });
export const assignMailToLead = (leadId: number, messageId: number) =>
  post<AssignMailResult>("/api/console/lead/assign-mail", { leadId, messageId });

// Brief 20 P2 — modifica inline (whitelist: name/expected_revenue/probability/stage_id/email_from/cf_date_next_followup).
export type UpdateLeadResult = { ok?: boolean; leadId?: number; stageId?: number; stageName?: string; expectedRevenue?: number; probability?: number; name?: string; emailFrom?: string; message?: string };
export const updateLead = (leadId: number, values: Record<string, unknown>) =>
  post<UpdateLeadResult>("/api/console/lead/update", { leadId, values });

// Brief 20 B — stato attività reale (neutral = grigio, mai rosso falso).
export const activityLabel: Record<string, { label: string; color: string }> = {
  fresh: { label: "Attivo", color: "#2F6B4F" },
  warning: { label: "Da seguire", color: "#C8A43A" },
  danger: { label: "Fermo", color: "#B23B3B" },
  neutral: { label: "Nessuna attività", color: "#8A8A8A" },
};

export const rottingLabel: Record<string, { label: string; color: string }> = {
  fresh: { label: "Fresco", color: "#2F6B4F" },
  warning: { label: "In raffreddamento", color: "#C8A43A" },
  danger: { label: "A rischio", color: "#B23B3B" },
  dead: { label: "Morto", color: "#7A2E2E" },
};

export const timelineMeta: Record<TimelineKind, { label: string; color: string; icon: string }> = {
  mail: { label: "Mail", color: "#6B4A1E", icon: "✉" },
  campionatura: { label: "Campionatura", color: "#2F6B4F", icon: "📦" },
  note: { label: "Nota", color: "#8A8A8A", icon: "•" },
};
