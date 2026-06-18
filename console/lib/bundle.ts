// getPartnerBundle(partnerId): UN bundle relazione-per-partner, con cache.
// Consumato da TUTTE le viste (contatto, inbox, lead, pipeline card, dossier).
import type {
  PartnerBundle, Lead, Dossier, Order, MailMessage, Partner, SenderResolution, OperatorKey, RegiaData, InboxData, PipelineData, DossierView, FollowupData, FairData,
} from "./types";
import type { MailAccount, MailListItem, MailDetail, PartnerListItem } from "./types";
import { shouldUseMock, searchRead, callKw } from "./odoo";
import { mockBundle, mockResolveBySender, mockRegia, mockInbox, mockPipeline, mockDossier, mockFollowup, mockFiere } from "./mock";
import { operatorFromLogin, operatorFromName } from "./theme";

function stripHtml(h: string | null): string | null {
  if (!h) return null;
  return h.replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ").replace(/&nbsp;/gi, " ").replace(/\s+/g, " ").trim() || null;
}

/** Le 2 caselle (Antonio + Martina). Read-only. */
export async function getMailAccounts(): Promise<MailAccount[]> {
  if (shouldUseMock()) {
    return [
      { id: 1, name: "Antonio Folino", operator: "antonio", responsibleName: "Antonio Folino" },
      { id: 2, name: "Martina Sinopoli", operator: "martina", responsibleName: "Martina Sinopoli" },
    ];
  }
  const rows = await searchRead<Record<string, unknown>>("casafolino.mail.account",
    [["active", "=", true]], { fields: ["name", "responsible_user_id"], order: "id" });
  return rows.map((a) => ({
    id: a.id as number, name: str(a.name) ?? "Casella",
    operator: operatorFromName(relName(a.responsible_user_id) ?? str(a.name)) as OperatorKey,
    responsibleName: relName(a.responsible_user_id),
  }));
}

/** Inbox mail (inbound). Filtrabile per casella. Read-only. */
export async function getMailList(accountId?: number): Promise<MailListItem[]> {
  if (shouldUseMock()) {
    const mock: MailListItem[] = [
      { id: 7001, subject: "Richiesta listino creme — Q3", senderName: "Klaus Berger", senderEmail: "klaus@berger-gourmet.de", date: "2026-06-16T09:12:00Z", accountId: 1, accountName: "Antonio Folino", operator: "antonio", partnerId: 9001, partnerName: "Berger Gourmet GmbH", linked: true, isRead: false, direction: "inbound" },
      { id: 7101, subject: "Anfrage Sortiment", senderName: "H. Neumann", senderEmail: "h.neumann@neumann-feinkost.at", date: "2026-06-17T07:30:00Z", accountId: 2, accountName: "Martina Sinopoli", operator: "martina", partnerId: null, partnerName: null, linked: false, isRead: false, direction: "inbound" },
    ];
    return mock.filter((m) => !accountId || m.accountId === accountId);
  }
  const domain: unknown[] = [["direction", "=", "inbound"], ["is_deleted", "=", false]];
  if (accountId) domain.push(["account_id", "=", accountId]);
  const rows = await searchRead<Record<string, unknown>>("casafolino.mail.message", domain,
    { fields: ["subject", "sender_email", "sender_name", "email_date", "partner_id", "account_id", "state", "is_read", "direction"], order: "email_date desc", limit: 200 });
  return rows.map((r) => {
    const partnerId = rel(r.partner_id);
    return {
      id: r.id as number, subject: str(r.subject) ?? "(senza oggetto)",
      senderName: str(r.sender_name) ?? str(r.sender_email) ?? "mittente",
      senderEmail: str(r.sender_email) ?? "", date: str(r.email_date),
      accountId: rel(r.account_id), accountName: relName(r.account_id) ?? "",
      operator: operatorFromName(relName(r.account_id)) as OperatorKey,
      partnerId, partnerName: relName(r.partner_id), linked: partnerId != null,
      isRead: r.is_read === true, direction: r.direction === "outbound" ? "outbound" : "inbound",
    };
  });
}

/** Dettaglio mail (corpo + contesto). Read-only. */
export async function getMailMessage(id: number): Promise<MailDetail | null> {
  if (shouldUseMock()) {
    const l = (await getMailList()).find((m) => m.id === id);
    if (!l) return null;
    return { ...l, body: "Corpo mail (mock). Per il Q3 valutiamo le creme a marchio nostro…", accountName: l.accountName };
  }
  const rows = await searchRead<Record<string, unknown>>("casafolino.mail.message",
    [["id", "=", id]],
    { fields: ["subject", "sender_email", "sender_name", "email_date", "partner_id", "account_id", "body_plain", "body_html", "snippet", "direction"], limit: 1 });
  if (!rows[0]) return null;
  const r = rows[0];
  return {
    id: r.id as number, subject: str(r.subject) ?? "(senza oggetto)",
    senderName: str(r.sender_name) ?? "", senderEmail: str(r.sender_email) ?? "",
    date: str(r.email_date), accountName: relName(r.account_id) ?? "",
    operator: operatorFromName(relName(r.account_id)) as OperatorKey,
    body: str(r.body_plain) ?? stripHtml(str(r.body_html)) ?? str(r.snippet) ?? "",
    partnerId: rel(r.partner_id), partnerName: relName(r.partner_id),
    direction: r.direction === "outbound" ? "outbound" : "inbound",
  };
}

/** Elenco partner (lente dossier). Read-only. */
export async function getPartnerList(q?: string): Promise<PartnerListItem[]> {
  if (shouldUseMock()) {
    return [
      { id: 9001, name: "Berger Gourmet GmbH", sub: "München · DE · klaus@berger-gourmet.de" },
      { id: 9002, name: "Neumann Feinkost", sub: "Wien · AT" },
    ].filter((p) => !q || p.name.toLowerCase().includes(q.toLowerCase()));
  }
  const domain: unknown[] = [["is_company", "=", true]];
  if (q && q.trim()) domain.push(["name", "ilike", q.trim()]);
  const rows = await searchRead<Record<string, unknown>>("res.partner", domain,
    { fields: ["name", "city", "country_id", "email"], order: "name", limit: 60 });
  return rows.map((p) => ({
    id: p.id as number, name: str(p.name) ?? "Partner",
    sub: [str(p.city), relName(p.country_id), str(p.email)].filter(Boolean).join(" · "),
  }));
}

/** Follow-up 4 colonne. Mock-first. Odoo: crm.lead per data follow-up/rotting. (verify on stage) */
export async function getFollowup(): Promise<FollowupData> {
  if (shouldUseMock()) return mockFollowup();
  const leads = await searchRead<Record<string, unknown>>("crm.lead",
    [["type", "=", "opportunity"], ["active", "=", true]],
    { fields: ["name", "partner_id", "expected_revenue", "user_id", "cf_date_next_followup", "cf_rotting_state", "cf_lead_score"], limit: 400 });
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const in7 = new Date(today.getTime() + 7 * 86400000);
  const item = (l: Record<string, unknown>, label: string) => ({
    id: l.id as number, partnerId: rel(l.partner_id), name: relName(l.partner_id) ?? str(l.name) ?? "Lead",
    sub: str(l.name) ?? "", operator: operatorFromLogin(relName(l.user_id)) as OperatorKey,
    value: num(l.expected_revenue), dateLabel: label,
  });
  const cols = { overdue: [] as ReturnType<typeof item>[], week: [] as ReturnType<typeof item>[], noplan: [] as ReturnType<typeof item>[], hot: [] as ReturnType<typeof item>[] };
  for (const l of leads) {
    const d = str(l.cf_date_next_followup);
    const due = d ? new Date(d) : null;
    if (!due) { if ((num(l.cf_lead_score) ?? 0) >= 70) cols.hot.push(item(l, "cliente caldo")); else cols.noplan.push(item(l, "senza data")); }
    else if (due < today) cols.overdue.push(item(l, "scaduto"));
    else if (due <= in7) cols.week.push(item(l, due.toISOString().slice(0, 10)));
    else if ((num(l.cf_lead_score) ?? 0) >= 70) cols.hot.push(item(l, "cliente caldo"));
  }
  return {
    source: "odoo",
    columns: [
      { key: "overdue", label: "Scaduti / oggi", tone: "danger", items: cols.overdue },
      { key: "week", label: "Prossimi 7 giorni", tone: "warn", items: cols.week },
      { key: "noplan", label: "Da pianificare", tone: "neutral", items: cols.noplan },
      { key: "hot", label: "Clienti caldi", tone: "ok", items: cols.hot },
    ],
  };
}

/** Fiere. Mock-first. Odoo: cf.export.fair. (verify on stage) */
export async function getFiere(): Promise<FairData> {
  if (shouldUseMock()) return mockFiere();
  const rows = await searchRead<Record<string, unknown>>("cf.export.fair", [],
    { fields: ["name", "location", "date_start", "state", "lead_count", "revenue_generated"], order: "date_start desc", limit: 50 });
  const toneOf = (s: string | null): FairData["fairs"][number]["statusTone"] =>
    s === "followup" ? "ok" : s === "done" || s === "closed" ? "neutral" : "warn";
  return {
    source: "odoo",
    fairs: rows.map((f) => ({
      id: f.id as number, name: str(f.name) ?? "Fiera", location: str(f.location) ?? "",
      dateLabel: str(f.date_start) ?? "data da definire", status: str(f.state) ?? "",
      statusTone: toneOf(str(f.state)), leads: num(f.lead_count) ?? 0, revenue: num(f.revenue_generated) ?? 0,
    })),
  };
}

/** Dossier 360. Mock-first. Odoo: project.project (dossier attivo più recente) + samples. (verify on stage) */
export async function getDossier(): Promise<DossierView> {
  if (shouldUseMock()) return mockDossier();
  const rows = await searchRead<Record<string, unknown>>("project.project",
    [["cf_status_dossier", "!=", false]],
    { fields: ["name", "cf_status_dossier", "partner_id", "cf_buyer_id", "user_id", "cf_dossier_value_estimate", "cf_lead_count", "cf_sample_count"], order: "write_date desc", limit: 1 });
  if (!rows[0]) {
    return { id: 0, name: "", status: "", statusTone: "neutral", partnerId: null, partnerName: "", country: null,
      operator: "other", valueEstimate: null, kpis: { leads: 0, samples: 0, orders: 0, revenue: 0, issues: 0 }, samples: [], source: "odoo" };
  }
  const d = rows[0];
  const partnerId = rel(d.partner_id) ?? rel(d.cf_buyer_id);
  const sampleRows = await searchRead<Record<string, unknown>>("cf.export.sample",
    [["project_id", "=", d.id]], { fields: ["reference", "state", "product_summary"], limit: 20 });
  const statusOf = (s: string | null): DossierView["statusTone"] =>
    s === "won" || s === "active" ? "ok" : s === "on_hold" ? "warn" : "neutral";
  return {
    id: d.id as number, name: str(d.name) ?? "Dossier", status: str(d.cf_status_dossier) ?? "",
    statusTone: statusOf(str(d.cf_status_dossier)), partnerId, partnerName: relName(d.partner_id) ?? relName(d.cf_buyer_id) ?? "Partner",
    country: null, operator: operatorFromLogin(relName(d.user_id)) as OperatorKey,
    valueEstimate: num(d.cf_dossier_value_estimate),
    kpis: { leads: num(d.cf_lead_count) ?? 0, samples: num(d.cf_sample_count) ?? sampleRows.length, orders: 0, revenue: 0, issues: 0 },
    samples: sampleRows.map((s) => ({
      id: s.id as number, name: str(s.reference) ?? "Campione", sub: str(s.product_summary) ?? "",
      statusLabel: str(s.state) ?? "", statusTone: (s.state === "feedback_ok" ? "ok" : s.state === "feedback_ko" ? "danger" : "warn") as DossierView["samples"][number]["statusTone"],
    })),
    source: "odoo",
  };
}

/** Pipeline kanban. Mock-first. Odoo: crm.lead raggruppati per stage_id. (verify on stage) */
export async function getPipeline(): Promise<PipelineData> {
  if (shouldUseMock()) return mockPipeline();
  const stages = await searchRead<Record<string, unknown>>("crm.stage", [], { fields: ["name", "sequence"], order: "sequence, id" });
  const leadRows = await searchRead<Record<string, unknown>>("crm.lead",
    [["type", "=", "opportunity"], ["active", "=", true]],
    { fields: ["name", "stage_id", "expected_revenue", "cf_lead_score", "user_id", "cf_rotting_state", "partner_id"], limit: 500, order: "expected_revenue desc" });
  const columns = stages.map((s) => {
    const sid = s.id as number;
    const name = relName(s.name) ?? str(s.name) ?? "Stage";
    const cards = leadRows.filter((l) => rel(l.stage_id) === sid).slice(0, 8).map((l) => {
      const ownerEmail = relName(l.user_id);
      return {
        id: l.id as number, partnerId: rel(l.partner_id), name: str(l.name) ?? "Lead",
        sub: relName(l.partner_id) ?? "", operator: operatorFromLogin(ownerEmail) as OperatorKey,
        value: num(l.expected_revenue), score: num(l.cf_lead_score),
        badgeLabel: l.cf_rotting_state === "danger" || l.cf_rotting_state === "dead" ? "scaduto" : null,
        badgeTone: "danger" as const,
      };
    });
    return { key: String(sid), label: name, count: leadRows.filter((l) => rel(l.stage_id) === sid).length, won: /vint|won/i.test(name), cards };
  });
  return { columns, source: "odoo" };
}

/** Inbox 3-pane. Mock-first. Odoo: casafolino.mail.message inbound da gestire. (verify on stage) */
export async function getInbox(): Promise<InboxData> {
  if (shouldUseMock()) return mockInbox();
  const rows = await searchRead<Record<string, unknown>>("casafolino.mail.message",
    [["direction", "=", "inbound"], ["state", "in", ["new", "review", "keep", "auto_keep"]], ["is_deleted", "=", false]],
    { fields: ["subject", "sender_email", "sender_name", "email_date", "partner_id", "match_type", "snippet"], order: "email_date desc", limit: 30 });
  const items = rows.map((r) => {
    const partnerId = rel(r.partner_id);
    const match = (str(r.match_type) as "exact" | "domain" | "manual" | "none") ?? "none";
    return {
      id: r.id as number, partnerId, operator: "other" as OperatorKey,
      name: str(r.sender_name) ?? str(r.sender_email) ?? "mittente",
      org: relName(r.partner_id) ?? str(r.sender_email) ?? "",
      badgeLabel: partnerId ? "Tocca a noi" : "no match",
      badgeTone: (partnerId ? "ok" : "danger") as InboxData["items"][number]["badgeTone"],
      resolutionMatch: match === "manual" ? "exact" : (match as "exact" | "domain" | "none"),
      message: {
        subject: str(r.subject) ?? "(senza oggetto)", senderName: str(r.sender_name) ?? "",
        senderEmail: str(r.sender_email) ?? "", timeLabel: str(r.email_date) ?? "",
        body: str(r.snippet) ?? "",
      },
    };
  });
  return { items, selectedId: items[0]?.id ?? 0, source: "odoo" };
}

/** Dati Regia (home). Mock-first; path Odoo best-effort via conteggi. */
export async function getRegia(): Promise<RegiaData> {
  if (shouldUseMock()) return mockRegia();
  const [hotLeads, overdueFollowups, blockedDossiers] = await Promise.all([
    callKw<number>("crm.lead", "search_count", [[["cf_lead_score", ">=", 70], ["type", "=", "opportunity"]]]),
    callKw<number>("crm.lead", "search_count", [[["cf_rotting_state", "in", ["danger", "dead"]], ["type", "=", "opportunity"]]]),
    callKw<number>("project.project", "search_count", [[["cf_status_dossier", "=", "on_hold"]]]),
  ]);
  return {
    greetingName: "Antonio",
    subtitle: "",
    kpis: { hotLeads, overdueFollowups, blockedDossiers, monthRevenue: 0 },
    queue: [],
    pipeline: { totalLeads: 0, segments: [] },
    source: "odoo",
  };
}

// --- cache in-memory (per processo server), TTL breve ---
const TTL_MS = 30_000;
const cache = new Map<number, { at: number; bundle: PartnerBundle }>();

export function invalidatePartner(partnerId: number): void {
  cache.delete(partnerId);
}

export async function getPartnerBundle(partnerId: number): Promise<PartnerBundle | null> {
  const hit = cache.get(partnerId);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.bundle;

  const bundle = shouldUseMock() ? mockBundle(partnerId) : await fetchFromOdoo(partnerId);
  if (bundle) cache.set(partnerId, { at: Date.now(), bundle });
  return bundle;
}

export async function resolveBySender(email: string): Promise<SenderResolution> {
  if (shouldUseMock()) return mockResolveBySender(email);
  const e = email.trim().toLowerCase();
  const domain = e.includes("@") ? e.split("@")[1] : null;
  const exact = await searchRead<{ id: number; name: string }>(
    "res.partner", [["email", "=ilike", e]], { fields: ["id", "name"], limit: 1 },
  );
  if (exact[0]) return { partnerId: exact[0].id, matchType: "exact", guessName: exact[0].name };
  if (domain) {
    const dom = await searchRead<{ id: number; name: string }>(
      "res.partner", [["email", "=ilike", `%@${domain}`], ["is_company", "=", true]],
      { fields: ["id", "name"], limit: 1 },
    );
    if (dom[0]) return { partnerId: dom[0].id, matchType: "domain", guessName: dom[0].name };
  }
  return { partnerId: null, matchType: "none", guessName: null };
}

// --- path Odoo reale (attivo quando CONSOLE_USE_MOCK=0 + credenziali) ---
function rel(v: unknown): number | null {
  return Array.isArray(v) && typeof v[0] === "number" ? v[0] : null;
}
function relName(v: unknown): string | null {
  return Array.isArray(v) && typeof v[1] === "string" ? v[1] : null;
}
function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}
function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

async function fetchFromOdoo(partnerId: number): Promise<PartnerBundle | null> {
  const partnerRows = await searchRead<Record<string, unknown>>(
    "res.partner", [["id", "=", partnerId]],
    { fields: ["name", "email", "phone", "country_id", "city", "cf_partner_role", "is_company"], limit: 1 },
  );
  if (!partnerRows[0]) return null;
  const p = partnerRows[0];
  const email = str(p.email);
  const domain = email && email.includes("@") ? email.split("@")[1] : null;

  const [leadRows, dossierRows, orderRows, mailRows] = await Promise.all([
    searchRead<Record<string, unknown>>("crm.lead",
      [["partner_id", "=", partnerId], ["type", "=", "opportunity"]],
      { fields: ["name", "stage_id", "expected_revenue", "probability", "user_id", "cf_lead_score", "cf_rotting_state", "cf_date_next_followup", "cf_project_id"], order: "expected_revenue desc" }),
    searchRead<Record<string, unknown>>("project.project",
      [["partner_id", "=", partnerId]],
      { fields: ["name", "cf_status_dossier", "cf_dossier_priority", "cf_dossier_value_estimate", "user_id"] }),
    searchRead<Record<string, unknown>>("sale.order",
      [["partner_id", "=", partnerId], ["state", "not in", ["draft", "cancel"]]],
      { fields: ["name", "amount_total", "state", "date_order", "cf_is_sample_order"], order: "date_order desc" }),
    searchRead<Record<string, unknown>>("casafolino.mail.message",
      ["|", ["partner_id", "=", partnerId], ...(domain ? [["sender_domain", "=", domain]] : [["id", "=", -1]]),
       ["state", "not in", ["auto_discard", "discard"]]],
      { fields: ["subject", "sender_email", "sender_name", "email_date", "direction", "is_read", "match_type", "snippet", "lead_id", "ai_category", "ai_urgency", "intent_detected"], order: "email_date desc", limit: 100 }),
  ]);

  const leads: Lead[] = leadRows.map((l) => {
    const ownerEmail = relName(l.user_id);
    return {
      id: l.id as number, name: (str(l.name) ?? "Lead"), stage: relName(l.stage_id),
      expectedRevenue: num(l.expected_revenue), probability: num(l.probability),
      ownerEmail, operator: operatorFromLogin(ownerEmail) as OperatorKey,
      score: num(l.cf_lead_score),
      rottingState: (str(l.cf_rotting_state) as Lead["rottingState"]) ?? null,
      nextFollowup: str(l.cf_date_next_followup), dossierId: rel(l.cf_project_id),
    };
  });

  const dossiers: Dossier[] = dossierRows.map((d) => {
    const ownerEmail = relName(d.user_id);
    return {
      id: d.id as number, name: (str(d.name) ?? "Dossier"),
      status: str(d.cf_status_dossier), priority: str(d.cf_dossier_priority),
      valueEstimate: num(d.cf_dossier_value_estimate), ownerEmail,
      operator: operatorFromLogin(ownerEmail) as OperatorKey,
    };
  });

  const orders: Order[] = orderRows.map((o) => ({
    id: o.id as number, name: (str(o.name) ?? ""), amountTotal: num(o.amount_total) ?? 0,
    state: (str(o.state) ?? ""), dateOrder: str(o.date_order), isSample: o.cf_is_sample_order === true,
  }));

  const mailThread: MailMessage[] = mailRows.map((m) => ({
    id: m.id as number, subject: str(m.subject), senderEmail: str(m.sender_email),
    senderName: str(m.sender_name), date: str(m.email_date),
    direction: m.direction === "outbound" ? "outbound" : "inbound",
    isRead: m.is_read === true, matchType: (str(m.match_type) as MailMessage["matchType"]) ?? "none",
    snippet: str(m.snippet), leadId: rel(m.lead_id), aiCategory: str(m.ai_category),
    aiUrgency: str(m.ai_urgency), intent: str(m.intent_detected),
  }));

  const realOrders = orders.filter((o) => !o.isSample);
  const revenueTotal = realOrders.reduce((s, o) => s + o.amountTotal, 0);
  const unread = mailThread.filter((m) => m.direction === "inbound" && !m.isRead).length;

  const partner: Partner = {
    id: partnerId, name: (str(p.name) ?? "Partner"), email, domain,
    phone: str(p.phone), country: relName(p.country_id), city: str(p.city),
    role: str(p.cf_partner_role), isCompany: p.is_company === true,
  };

  return {
    partner, leads, dossiers, orders,
    revenue: { total: revenueTotal, currency: "EUR", orderCount: orders.length },
    mailThread,
    signals: {
      hotnessTier: null, hotnessScore: null, nbaText: null, nbaUrgency: null,
      unreadMail: unread, overdueFollowup: leads.some((l) => l.rottingState === "danger" || l.rottingState === "dead"),
    },
    source: "odoo",
  };
}
