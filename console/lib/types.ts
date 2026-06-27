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
  isDossier?: boolean;            // pin dossier curato (console)
  dossierFolderId?: number | false;
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

// --- Inbox (3-pane) ---
export interface InboxSelectedMessage {
  subject: string;
  senderName: string;
  senderEmail: string;
  timeLabel: string;
  body: string;
}

export interface InboxItem {
  id: number;
  partnerId: number | null; // null = mittente non risolto (no match)
  operator: OperatorKey;
  name: string;
  org: string;
  badgeLabel: string | null;
  badgeTone: Tone;
  resolutionMatch: "exact" | "domain" | "none";
  message: InboxSelectedMessage;
  state: string; // stato triage corrente (per undo: stato precedente)
  senderEmail: string; // per "seleziona tutti da questo mittente"
  accountId: number | null; // casella di appartenenza (multi-casella)
  accountName: string;
}

export interface InboxData {
  items: InboxItem[];
  selectedId: number;
  source: "odoo" | "mock";
}

// --- Pipeline (kanban) ---
export interface PipelineCard {
  id: number;
  partnerId: number | null;
  name: string;
  sub: string;
  operator: OperatorKey;
  value: number | null;
  score: number | null;
  badgeLabel: string | null;
  badgeTone: Tone;
}

export interface PipelineColumn {
  key: string;
  label: string;
  count: number;
  won: boolean;
  cards: PipelineCard[];
}

export interface PipelineData {
  columns: PipelineColumn[];
  source: "odoo" | "mock";
}

// --- Dossier 360 ---
export interface DossierSample {
  id: number;
  name: string;
  sub: string;
  statusLabel: string;
  statusTone: Tone;
}

export interface DossierView {
  id: number;
  name: string;
  status: string;
  statusTone: Tone;
  partnerId: number | null;
  partnerName: string;
  country: string | null;
  operator: OperatorKey;
  valueEstimate: number | null;
  kpis: { leads: number; samples: number; orders: number; revenue: number; issues: number };
  samples: DossierSample[];
  source: "odoo" | "mock";
}

// --- Follow-up (4 colonne) ---
export interface FollowupItem {
  id: number;
  partnerId: number | null;
  name: string;
  sub: string;
  operator: OperatorKey;
  value: number | null;
  dateLabel: string;
}
export interface FollowupColumn { key: string; label: string; tone: Tone; items: FollowupItem[]; }
export interface FollowupData { columns: FollowupColumn[]; source: "odoo" | "mock"; }

// --- Fiere ---
export interface Fair {
  id: number;
  name: string;
  location: string;
  dateLabel: string;
  status: string;
  statusTone: Tone;
  leads: number;
  revenue: number;
}
export interface FairData { fairs: Fair[]; source: "odoo" | "mock"; }

// --- Mail (2 caselle: Antonio + Martina) — read-only ---
export interface MailAccount {
  id: number;
  name: string;
  operator: OperatorKey;
  responsibleName: string | null;
}
export interface MailListItem {
  id: number;
  subject: string;
  senderName: string;
  senderEmail: string;
  date: string | null; // ISO
  accountId: number | null;
  accountName: string;
  operator: OperatorKey;
  partnerId: number | null;     // risolto dal record (casafolino_mail)
  partnerName: string | null;
  linked: boolean;              // false = "non collegato" (mai campo muto)
  isRead: boolean;
  direction: "inbound" | "outbound";
}
export interface MailDetail {
  id: number;
  subject: string;
  senderName: string;
  senderEmail: string;
  date: string | null;
  accountName: string;
  operator: OperatorKey;
  body: string;
  partnerId: number | null;
  partnerName: string | null;
  direction: "inbound" | "outbound";
}

// --- Dossier browser (lente su res.partner) ---
export interface PartnerListItem {
  id: number;
  name: string;
  sub: string;
}
