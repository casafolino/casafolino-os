// Bozza AI via Groq (server-only). Chiave: GROQ_API_KEY (.env) o casafolino.groq_api_key da Odoo.
// NON usa cf.gemini.client. Mock-first: senza chiave/mock restituisce una bozza locale.
import { shouldUseMock, getConfigParam } from "./odoo";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";

export interface DraftInput {
  subject: string;
  body: string;
  instruction?: string;
  partnerName?: string;
}

async function groqKey(): Promise<string | null> {
  if (process.env.GROQ_API_KEY) return process.env.GROQ_API_KEY;
  if (!shouldUseMock()) {
    try { return await getConfigParam("casafolino.groq_api_key"); } catch { return null; }
  }
  return null;
}

export async function generateAiDraft(input: DraftInput): Promise<{ draft: string; source: "groq" | "mock" }> {
  const key = await groqKey();
  if (!key) {
    return {
      source: "mock",
      draft:
        `Gentile ${input.partnerName || "cliente"},\n\n` +
        `grazie per il messaggio "${input.subject}". ` +
        `Le confermo che procediamo: in allegato troverà il listino EXW aggiornato con MOQ e palletizzazione.\n\n` +
        `Resto a disposizione per definire i volumi.\n\nCordiali saluti,\nAntonio Folino — CasaFolino` +
        (input.instruction ? `\n\n(istruzione applicata: ${input.instruction})` : ""),
    };
  }
  const res = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
      "User-Agent": "Mozilla/5.0", // evita Cloudflare 403 (cfr. AGENTS.md)
    },
    body: JSON.stringify({
      model: MODEL,
      temperature: 0.3,
      max_tokens: 500,
      messages: [
        { role: "system", content: "Sei l'assistente commerciale di CasaFolino. Scrivi bozze email professionali, concise, in italiano (o nella lingua del cliente se evidente). Non inventare dati: lascia placeholder se mancano." },
        { role: "user", content: `Email ricevuta — oggetto: ${input.subject}\n\n${input.body}\n\nIstruzione: ${input.instruction || "rispondi in modo utile e professionale"}` },
      ],
    }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Groq HTTP ${res.status}`);
  const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  return { draft: data.choices?.[0]?.message?.content?.trim() || "(bozza vuota)", source: "groq" };
}
