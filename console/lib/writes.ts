// Scritture — SOLO via Odoo (server-side). Mai SMTP raw: la mail passa da mail.mail.
// Mock-safe: senza credenziali simula l'esito senza toccare Odoo.
import { shouldUseMock, callKw, searchRead } from "./odoo";
import { invalidatePartner } from "./bundle";

export interface WriteResult { ok: boolean; id?: number; simulated?: boolean; message: string; }

/** Crea un crm.lead (opportunità). */
export async function createLead(input: { partnerId?: number | null; name: string; emailFrom?: string }): Promise<WriteResult> {
  if (shouldUseMock()) return { ok: true, id: 0, simulated: true, message: `Lead "${input.name}" creato (mock)` };
  const id = await callKw<number>("crm.lead", "create", [{
    name: input.name,
    type: "opportunity",
    ...(input.partnerId ? { partner_id: input.partnerId } : {}),
    ...(input.emailFrom ? { email_from: input.emailFrom } : {}),
  }]);
  if (input.partnerId) invalidatePartner(input.partnerId);
  return { ok: true, id, message: `Lead creato (id ${id})` };
}

/** Collega una casafolino.mail.message a un lead esistente. */
export async function linkMessageToLead(input: { messageId: number; leadId: number }): Promise<WriteResult> {
  if (shouldUseMock()) return { ok: true, simulated: true, message: `Mail ${input.messageId} collegata al lead ${input.leadId} (mock)` };
  await callKw<boolean>("casafolino.mail.message", "write", [[input.messageId], { lead_id: input.leadId }]);
  return { ok: true, message: "Mail collegata al lead" };
}

// Il service-user console_api NON ha email configurata: message_post/notify di Odoo
// solleverebbe "configure the sender's email address". Attribuiamo nota/task al PARTNER
// dell'operatore umano (sessione) → autore valido + attribution corretta. Cache uid→partner.
const _operatorPartnerCache = new Map<number, number>();
async function operatorPartnerId(operatorUid?: number): Promise<number | null> {
  if (!operatorUid) return null;
  if (_operatorPartnerCache.has(operatorUid)) return _operatorPartnerCache.get(operatorUid)!;
  const rows = await callKw<Record<string, unknown>[]>("res.users", "read", [[operatorUid], ["partner_id"]]);
  const pid = Array.isArray(rows?.[0]?.partner_id) ? Number((rows[0].partner_id as [number, string])[0]) : null;
  if (pid) _operatorPartnerCache.set(operatorUid, pid);
  return pid;
}

/** Nota interna su un lead (chatter nativo: mail.message via message_post). Nessun campo custom. */
export async function postLeadNote(input: { leadId: number; body: string; operatorUid?: number }): Promise<WriteResult> {
  const body = (input.body || "").trim();
  if (!body) return { ok: false, message: "Nota vuota." };
  if (shouldUseMock()) return { ok: true, simulated: true, message: "Nota registrata (mock)" };
  const authorId = await operatorPartnerId(input.operatorUid);
  const msgId = await callKw<number>("crm.lead", "message_post", [[input.leadId]], {
    body,
    message_type: "comment",
    subtype_xmlid: "mail.mt_note",
    ...(authorId ? { author_id: authorId } : {}),
  });
  return { ok: true, id: msgId, message: "Nota registrata" };
}

/** Attività futura su un lead (mail.activity nativo, con scadenza). Nessun campo custom. */
export async function createLeadActivity(input: {
  leadId: number;
  summary: string;
  dueDate: string; // YYYY-MM-DD
  operatorUid?: number;
}): Promise<WriteResult> {
  const summary = (input.summary || "").trim();
  if (!summary) return { ok: false, message: "Descrizione attività mancante." };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.dueDate)) return { ok: false, message: "Data attività non valida." };
  if (shouldUseMock()) return { ok: true, simulated: true, message: `Attività "${summary}" pianificata (mock)` };
  const [modelRow] = await searchRead<{ id: number }>("ir.model", [["model", "=", "crm.lead"]], { fields: ["id"], limit: 1 });
  if (!modelRow) return { ok: false, message: "Modello crm.lead non risolto." };
  const [todoRow] = await searchRead<{ res_id: number }>(
    "ir.model.data",
    [["module", "=", "mail"], ["name", "=", "mail_activity_data_todo"]],
    { fields: ["res_id"], limit: 1 }
  );
  const id = await callKw<number>("mail.activity", "create", [{
    res_model_id: modelRow.id,
    res_id: input.leadId,
    summary,
    date_deadline: input.dueDate,
    // assegna l'attività all'operatore umano (sessione); fallback = utente corrente (console_api).
    ...(input.operatorUid ? { user_id: input.operatorUid } : {}),
    ...(todoRow?.res_id ? { activity_type_id: todoRow.res_id } : {}),
  }]);
  return { ok: true, id, message: "Attività pianificata" };
}

/** Invia email tramite Odoo (mail.mail.create + send). MAI SMTP diretto. */
export async function sendMail(input: { to: string; subject: string; bodyHtml: string }): Promise<WriteResult> {
  if (shouldUseMock()) return { ok: true, simulated: true, message: `Email a ${input.to} accodata in mail.mail (mock)` };
  // SAFETY: su stage l'outbound SMTP è reale → blocca l'invio salvo abilitazione esplicita.
  if (process.env.CONSOLE_ALLOW_SEND !== "1") {
    return { ok: false, simulated: true, message: "Invio BLOCCATO (CONSOLE_ALLOW_SEND≠1): outbound stage non neutralizzato." };
  }
  const mailId = await callKw<number>("mail.mail", "create", [{
    email_to: input.to,
    subject: input.subject,
    body_html: input.bodyHtml,
  }]);
  await callKw<boolean>("mail.mail", "send", [[mailId]]);
  return { ok: true, id: mailId, message: `Email inviata via Odoo (mail.mail ${mailId})` };
}
