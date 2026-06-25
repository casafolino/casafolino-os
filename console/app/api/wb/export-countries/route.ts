// GET /api/wb/export-countries — conteggio paesi export attivi (distinct country_id clienti).
// Scene: vetrina, ufficio. Conteggio reale da Odoo, non hardcoded.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock } from "@/lib/odoo";
import { readGroup, m2oId } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

export const GET = wbHandler("export-countries", async () => {
  if (shouldUseMock()) return { count: 23 };
  // Clienti (customer_rank>0) con un paese impostato, raggruppati per country_id:
  // il numero di gruppi = paesi distinti serviti.
  const domain = [
    ["customer_rank", ">", 0],
    ["country_id", "!=", false],
  ];
  const groups = await readGroup("res.partner", domain, ["id"], ["country_id"]);
  const count = groups.filter((g) => m2oId(g.country_id) != null).length;
  return { count };
});
