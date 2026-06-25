// GET /api/wb/shipments-today — spedizioni in partenza oggi, per corriere.
// Scene: produzione, vetrina. Nessun campo importo.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock } from "@/lib/odoo";
import { readGroup, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface CarrierRow {
  carrier: string;
  count: number;
}

const MOCK: CarrierRow[] = [
  { carrier: "DHL Express", count: 3 },
  { carrier: "GLS", count: 2 },
  { carrier: "Ritiro cliente", count: 1 },
];

export const GET = wbHandler("shipments-today", async () => {
  if (shouldUseMock()) {
    return { rows: MOCK, total: MOCK.reduce((s, r) => s + r.count, 0) };
  }
  const today = todayISO();
  const domain = [
    ["picking_type_code", "=", "outgoing"],
    ["scheduled_date", ">=", `${today} 00:00:00`],
    ["scheduled_date", "<=", `${today} 23:59:59`],
  ];
  const groups = await readGroup("stock.picking", domain, ["id"], ["carrier_id"]);
  const rows: CarrierRow[] = groups.map((g) => ({
    carrier: m2oName(g.carrier_id) ?? "Senza corriere",
    count: typeof g.__count === "number" ? g.__count : 0,
  }));
  rows.sort((a, b) => b.count - a.count);
  return { rows, total: rows.reduce((s, r) => s + r.count, 0) };
});
