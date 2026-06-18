// Scritture — SOLO via Odoo (server-side). Mai SMTP raw: la mail passa da mail.mail.
// Mock-safe: senza credenziali simula l'esito senza toccare Odoo.
import { shouldUseMock, callKw } from "./odoo";
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
