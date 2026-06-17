// Tipi del data layer — il contratto del bundle relazione-per-partner.

export type OperatorKey = "antonio" | "josefina" | "martina" | "other";

export interface Partner {
  id: number;
  name: string;
  email: string | null;
  domain: string | null;
  phone: string | null;
  country: string | null;
  city: string | null;
  role: string | null; // cf_partner_role
  isCompany: boolean;
}

export interface MailMessage {
  id: number;
  subject: string | null;
  senderEmail: string | null;
  senderName: string | null;
  date: string | null; // ISO
  direction: "inbound" | "outbound";
  isRead: boolean;
  matchType: "exact" | "domain" | "manual" | "none";
  snippet: string | null;
  leadId: number | null;
  aiCategory: string | null;
  aiUrgency: string | null;
  intent: string | null;
}

export interface Lead {
  id: number;
  name: string;
  stage: string | null;
  expectedRevenue: number | null;
  probability: number | null;
  ownerEmail: string | null;
  operator: OperatorKey;
  score: number | null; // cf_lead_score
  rottingState: "ok" | "warning" | "danger" | "dead" | null;
  nextFollowup: string | null;
  dossierId: number | null; // cf_project_id
}

export interface Dossier {
  id: number;
  name: string;
  status: string | null; // cf_status_dossier
  priority: string | null; // cf_dossier_priority
  valueEstimate: number | null;
  ownerEmail: string | null;
  operator: OperatorKey;
}

export interface Order {
  id: number;
  name: string;
  amountTotal: number;
  state: string;
  dateOrder: string | null;
  isSample: boolean;
}

export interface Signals {
  hotnessTier: "hot" | "warm" | "cold" | null;
  hotnessScore: number | null;
  nbaText: string | null; // Next Best Action (suggerimento, non invio)
  nbaUrgency: string | null;
  unreadMail: number;
  overdueFollowup: boolean;
}

export interface PartnerBundle {
  partner: Partner;
  leads: Lead[];
  dossiers: Dossier[];
  orders: Order[];
  revenue: { total: number; currency: string; orderCount: number };
  mailThread: MailMessage[]; // casafolino.mail.message per partner (exact + domain)
  signals: Signals;
  source: "odoo" | "mock";
}

/** Risoluzione partner dal mittente di una mail non collegata (NON richiede un lead). */
export interface SenderResolution {
  partnerId: number | null;
  matchType: "exact" | "domain" | "none";
  guessName: string | null;
}

// --- Regia (home / command center) ---
export type Tone = "ok" | "warn" | "danger" | "neutral";

export interface RegiaQueueItem {
  partnerId: number | null;
  operator: OperatorKey;
  partnerName: string;
  subject: string;
  badgeLabel: string;
  badgeTone: Tone;
}

export interface RegiaData {
  greetingName: string;
  subtitle: string;
  kpis: { hotLeads: number; overdueFollowups: number; blockedDossiers: number; monthRevenue: number };
  queue: RegiaQueueItem[];
  pipeline: { totalLeads: number; segments: { label: string; pct: number; color: string }[] };
  source: "odoo" | "mock";
}
