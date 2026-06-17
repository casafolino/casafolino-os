// getPartnerBundle(partnerId): UN bundle relazione-per-partner, con cache.
// Consumato da TUTTE le viste (contatto, inbox, lead, pipeline card, dossier).
import type {
  PartnerBundle, Lead, Dossier, Order, MailMessage, Partner, SenderResolution, OperatorKey,
} from "./types";
import { shouldUseMock, searchRead } from "./odoo";
import { mockBundle, mockResolveBySender } from "./mock";
import { operatorFromLogin } from "./theme";

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
