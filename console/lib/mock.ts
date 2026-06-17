// Fixtures locali — UI verificabile senza Odoo (CONSOLE_USE_MOCK=1).
// Klaus Berger è la prova di "mail ovunque": le sue mail compaiono nel suo
// lead, dossier e ordini perché TUTTE le viste consumano lo stesso bundle.
import type { PartnerBundle, MailMessage, SenderResolution, RegiaData, InboxData, PipelineData, DossierView, FollowupData, FairData } from "./types";

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

export function mockRegia(): RegiaData {
  return {
    greetingName: "Antonio",
    subtitle: "martedì 17 giugno · 7 email ti aspettano",
    kpis: { hotLeads: 12, overdueFollowups: 5, blockedDossiers: 3, monthRevenue: 58000 },
    queue: [
      { partnerId: 9001, operator: "antonio", partnerName: "REWE Group", subject: "Richiesta listino creme Q3", badgeLabel: "scaduto 4g", badgeTone: "danger" },
      { partnerId: null, operator: "josefina", partnerName: "SPAR Österreich", subject: "Conferma campioni miele", badgeLabel: "oggi", badgeTone: "warn" },
      { partnerId: 9002, operator: "other", partnerName: "Delifrance", subject: "Primo contatto cantucci", badgeLabel: "nuovo", badgeTone: "neutral" },
    ],
    pipeline: {
      totalLeads: 87,
      segments: [
        { label: "Interesse", pct: 30, color: "#CBE4D2" },
        { label: "Trattativa", pct: 22, color: "#8FC79F" },
        { label: "Preventivo", pct: 24, color: "var(--op-antonio)" },
        { label: "Vinto", pct: 14, color: "#2F6B4F" },
        { label: "Chiuso", pct: 10, color: "#1F4A36" },
      ],
    },
    source: "mock",
  };
}

export function mockInbox(): InboxData {
  return {
    selectedId: 7001,
    source: "mock",
    items: [
      {
        id: 7001, partnerId: 9001, operator: "antonio", name: "Klaus Berger", org: "Berger Gourmet · listino Q3",
        badgeLabel: "Tocca a noi", badgeTone: "ok", resolutionMatch: "exact",
        message: { subject: "Richiesta listino creme — volumi Q3", senderName: "Klaus Berger", senderEmail: "klaus@berger-gourmet.de", timeLabel: "oggi 08:14",
          body: "Per il Q3 valutiamo le creme a marchio nostro. Mi serve il listino EXW con MOQ e palletizzazione per pistacchio e nocciola…" },
      },
      {
        id: 7101, partnerId: 9002, operator: "other", name: "H. Neumann", org: "Neumann Feinkost · sortiment",
        badgeLabel: null, badgeTone: "neutral", resolutionMatch: "domain",
        message: { subject: "Anfrage Sortiment", senderName: "H. Neumann", senderEmail: "h.neumann@neumann-feinkost.at", timeLabel: "oggi 07:30",
          body: "Wir interessieren uns für Ihr Sortiment italienischer Spezialitäten für unsere Feinkost-Abteilung…" },
      },
      {
        id: 7999, partnerId: null, operator: "other", name: "Delifrance", org: "primo contatto cantucci",
        badgeLabel: "no match", badgeTone: "danger", resolutionMatch: "none",
        message: { subject: "Première prise de contact — cantuccini", senderName: "Service Achats", senderEmail: "achats@delifrance.fr", timeLabel: "ieri 16:20",
          body: "Bonjour, nous souhaitons référencer vos cantuccini. Pourriez-vous nous transmettre votre catalogue…" },
      },
    ],
  };
}

export function mockPipeline(): PipelineData {
  return {
    source: "mock",
    columns: [
      { key: "interesse", label: "Interesse", count: 14, won: false, cards: [
        { id: 1, partnerId: null, name: "Edeka Süd", sub: "creme · DE", operator: "antonio", value: 24000, score: 62, badgeLabel: null, badgeTone: "neutral" },
        { id: 2, partnerId: null, name: "Migros", sub: "miele · CH", operator: "josefina", value: 31000, score: 55, badgeLabel: null, badgeTone: "neutral" },
      ]},
      { key: "trattativa", label: "Trattativa", count: 9, won: false, cards: [
        { id: 3, partnerId: 9001, name: "REWE Group", sub: "creme PL · DE", operator: "antonio", value: 48000, score: 78, badgeLabel: "scaduto", badgeTone: "danger" },
        { id: 4, partnerId: null, name: "SPAR ÖST", sub: "miele · AT", operator: "martina", value: 27000, score: 71, badgeLabel: null, badgeTone: "neutral" },
      ]},
      { key: "preventivo", label: "Preventivo", count: 5, won: false, cards: [
        { id: 5, partnerId: null, name: "Kaufland", sub: "cantucci · DE", operator: "antonio", value: 62000, score: 84, badgeLabel: null, badgeTone: "neutral" },
      ]},
      { key: "vinto", label: "Vinto", count: 3, won: true, cards: [
        { id: 6, partnerId: null, name: "Coop CH", sub: "creme · CH", operator: "josefina", value: 54000, score: null, badgeLabel: "vinto", badgeTone: "ok" },
      ]},
    ],
  };
}

export function mockDossier(): DossierView {
  return {
    id: 4201, name: "Creme PL Germania", status: "Attivo", statusTone: "ok",
    partnerId: 9001, partnerName: "Berger Gourmet GmbH", country: "DE", operator: "antonio",
    valueEstimate: 142000,
    kpis: { leads: 3, samples: 2, orders: 7, revenue: 142000, issues: 1 },
    samples: [
      { id: 1, name: "Creme pistacchio · 3 SKU", sub: "inviata 28 feb · valutazione 8/10", statusLabel: "Feedback ok", statusTone: "ok" },
      { id: 2, name: "Crema nocciola · 1 SKU", sub: "inviata 10 giu · feedback atteso", statusLabel: "In attesa", statusTone: "warn" },
    ],
    source: "mock",
  };
}

export function mockFollowup(): FollowupData {
  return {
    source: "mock",
    columns: [
      { key: "overdue", label: "Scaduti / oggi", tone: "danger", items: [
        { id: 1, partnerId: 9001, name: "REWE Group", sub: "listino creme Q3", operator: "antonio", value: 48000, dateLabel: "scaduto 4g" },
      ]},
      { key: "week", label: "Prossimi 7 giorni", tone: "warn", items: [
        { id: 2, partnerId: null, name: "SPAR ÖST", sub: "conferma campioni", operator: "martina", value: 27000, dateLabel: "19 giu" },
      ]},
      { key: "noplan", label: "Da pianificare", tone: "neutral", items: [
        { id: 3, partnerId: 9002, name: "Neumann Feinkost", sub: "primo contatto", operator: "other", value: null, dateLabel: "senza data" },
      ]},
      { key: "hot", label: "Clienti caldi", tone: "ok", items: [
        { id: 4, partnerId: null, name: "Kaufland", sub: "preventivo cantucci", operator: "antonio", value: 62000, dateLabel: "oggi" },
      ]},
    ],
  };
}

export function mockFiere(): FairData {
  return {
    source: "mock",
    fairs: [
      { id: 1, name: "Anuga 2026", location: "Köln · DE", dateLabel: "ott 2026", status: "In preparazione", statusTone: "warn", leads: 0, revenue: 0 },
      { id: 2, name: "TUTTOFOOD 2026", location: "Milano · IT", dateLabel: "mag 2026", status: "Follow-up", statusTone: "ok", leads: 34, revenue: 86000 },
      { id: 3, name: "SIAL Montréal", location: "Montréal · CA", dateLabel: "apr 2026", status: "Chiusa", statusTone: "neutral", leads: 18, revenue: 41000 },
    ],
  };
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
