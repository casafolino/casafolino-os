// GET /api/wb/mrp-active — produzioni in corso + % avanzamento.
// Scene: produzione, ufficio. Nessun campo importo.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface MrpRow {
  name: string;
  product: string;
  pct: number;
}

const MOCK: MrpRow[] = [
  { name: "MO/00231", product: "Nduja artigianale 200g", pct: 92 },
  { name: "MO/00232", product: "Olio EVO biologico 500ml", pct: 64 },
  { name: "MO/00233", product: "Sugo pomodoro datterino", pct: 18 },
  { name: "MO/00234", product: "Confettura fichi 240g", pct: 100 },
];

export const GET = wbHandler("mrp-active", async () => {
  if (shouldUseMock()) return { rows: MOCK };
  const domain = [["state", "in", ["confirmed", "progress", "to_close"]]];
  const recs = await searchRead<{
    name: string;
    product_id: unknown;
    product_qty: number;
    qty_producing: number;
  }>("mrp.production", domain, {
    fields: ["name", "product_id", "product_qty", "qty_producing"],
    order: "date_start asc",
    limit: 30,
  });
  const rows: MrpRow[] = recs.map((r) => {
    const total = r.product_qty || 0;
    const done = r.qty_producing || 0;
    const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
    return { name: r.name, product: m2oName(r.product_id) ?? "—", pct };
  });
  return { rows };
});
