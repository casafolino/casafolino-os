// Fixtures locali — UI verificabile senza Odoo (CONSOLE_USE_MOCK=1).
// Klaus Berger è la prova di "mail ovunque": le sue mail compaiono nel suo
// lead, dossier e ordini perché TUTTE le viste consumano lo stesso bundle.
import type { PartnerBundle, MailMessage, SenderResolution } from "./types";

const KLAUS_MAIL: MailMessage[] = [
  {
    id: 7001, subject: "Re: Listino private label Q3", senderEmail: "klaus@berger-gourmet.de",
    senderName: "Klaus Berger", date: "2026-06-16T09:12:00Z", direction: "inbound", isRead: false,
    matchType: "exact", snippet: "Danke für das Angebot. Können wir die Mengen für die Pesto-Linie...",
    leadId: 5101, aiCategory: "request_quote", aiUrgency: "high", intent: "request_quote",
  },
  {
    id: 7002, subject: "Listino private label Q3", senderEmail: "antonio@casafolino.com",
    senderName: "Antonio Folino", date: "2026-06-15T16:40:00Z", direction: "outbound", isRead: true,
    matchType: "exact", snippet: "Gentile Klaus, in allegato il listino aggiornato per la linea...",
    leadId: 5101, aiCategory: null, aiUrgency: null, intent: null,
  },
  {
    id: 7003, subject: "Campioni ricevuti — feedback", senderEmail: "einkauf@berger-gourmet.de",
    senderName: "Berger Einkauf", date: "2026-06-10T08:05:00Z", direction: "inbound", isRead: true,
    matchType: "domain", snippet: "Die Muster sind angekommen. Qualität sehr gut, besonders...",
    leadId: null, aiCategory: "feedback", aiUrgency: "medium", intent: "follow_up",
  },
];

const KLAUS_BUNDLE: PartnerBundle = {
  partner: {
    id: 9001, name: "Berger Gourmet GmbH", email: "klaus@berger-gourmet.de",
    domain: "berger-gourmet.de", phone: "+49 89 1234567", country: "DE", city: "München",
    role: "customer", isCompany: true,
  },
  leads: [
    {
      id: 5101, name: "Private label pesto — Berger Q3", stage: "Negoziazione",
      expectedRevenue: 48000, probability: 60, ownerEmail: "antonio@casafolino.com",
      operator: "antonio", score: 78, rottingState: "ok", nextFollowup: "2026-06-19",
      dossierId: 4201,
    },
    {
      id: 5102, name: "Linea olio EVO — esplorativo", stage: "Qualificazione",
      expectedRevenue: 15000, probability: 20, ownerEmail: "josefina.lazzaro@casafolino.com",
      operator: "josefina", score: 41, rottingState: "warning", nextFollowup: null,
      dossierId: null,
    },
  ],
  dossiers: [
    {
      id: 4201, name: "Dossier Berger — Private Label DE", status: "active",
      priority: "high", valueEstimate: 75000, ownerEmail: "antonio@casafolino.com",
      operator: "antonio",
    },
  ],
  orders: [
    { id: 6301, name: "S00231", amountTotal: 12400, state: "sale", dateOrder: "2026-05-20T10:00:00Z", isSample: false },
    { id: 6302, name: "S00198", amountTotal: 0, state: "sale", dateOrder: "2026-04-02T10:00:00Z", isSample: true },
  ],
  revenue: { total: 12400, currency: "EUR", orderCount: 2 },
  mailThread: KLAUS_MAIL,
  signals: {
    hotnessTier: "hot", hotnessScore: 82,
    nbaText: "Rispondi alla richiesta quantità Pesto (mail di ieri, alta urgenza).",
    nbaUrgency: "high", unreadMail: 1, overdueFollowup: false,
  },
  source: "mock",
};

// Secondo partner senza lead — prova: contesto inbox dal mittente anche senza lead collegato.
const NEUMANN_BUNDLE: PartnerBundle = {
  partner: {
    id: 9002, name: "Neumann Feinkost", email: "info@neumann-feinkost.at",
    domain: "neumann-feinkost.at", phone: null, country: "AT", city: "Wien",
    role: "prospect", isCompany: true,
  },
  leads: [],
  dossiers: [],
  orders: [],
  revenue: { total: 0, currency: "EUR", orderCount: 0 },
  mailThread: [
    {
      id: 7101, subject: "Anfrage Sortiment", senderEmail: "h.neumann@neumann-feinkost.at",
      senderName: "H. Neumann", date: "2026-06-17T07:30:00Z", direction: "inbound", isRead: false,
      matchType: "domain", snippet: "Wir interessieren uns für Ihr Sortiment italienischer...",
      leadId: null, aiCategory: "intro", aiUrgency: "medium", intent: "info_request",
    },
  ],
  signals: {
    hotnessTier: "warm", hotnessScore: 35,
    nbaText: "Nuovo contatto senza lead: qualifica e crea lead.",
    nbaUrgency: "medium", unreadMail: 1, overdueFollowup: false,
  },
  source: "mock",
};

const BUNDLES: Record<number, PartnerBundle> = {
  9001: KLAUS_BUNDLE,
  9002: NEUMANN_BUNDLE,
};

export function mockBundle(partnerId: number): PartnerBundle | null {
  return BUNDLES[partnerId] ?? null;
}

export function mockPartnerList(): PartnerBundle["partner"][] {
  return Object.values(BUNDLES).map((b) => b.partner);
}

export function mockResolveBySender(email: string): SenderResolution {
  const e = email.trim().toLowerCase();
  const domain = e.includes("@") ? e.split("@")[1] : null;
  for (const b of Object.values(BUNDLES)) {
    if (b.partner.email?.toLowerCase() === e) {
      return { partnerId: b.partner.id, matchType: "exact", guessName: b.partner.name };
    }
  }
  for (const b of Object.values(BUNDLES)) {
    if (domain && b.partner.domain === domain) {
      return { partnerId: b.partner.id, matchType: "domain", guessName: b.partner.name };
    }
  }
  return { partnerId: null, matchType: "none", guessName: null };
}
