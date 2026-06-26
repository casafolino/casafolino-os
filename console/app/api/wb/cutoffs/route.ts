// GET /api/wb/cutoffs — ordini outgoing ancora aperti (non done), per corriere.
// Scene: logistica, ufficio, direzione. Gli ORARI ritiro sono client-side (lib/wb/cutoffs.ts);
// qui ritorniamo solo il carico per corriere. Nessun campo importo.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock } from "@/lib/odoo";
import { readGroup, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface CarrierLoad {
  carrier: string;
  open: number;
}

const MOCK: CarrierLoad[] = [
  { carrier: "DHL Express", open: 5 },
  { carrier: "GLS", open: 2 },
  { carrier: "BRT", open: 0 },
];

export const GET = wbHandler("cutoffs", async () => {
  if (shouldUseMock()) return { rows: MOCK };
  const domain = [
    ["picking_type_code", "=", "outgoing"],
    ["state", "not in", ["done", "cancel"]],
  ];
  const groups = await readGroup("stock.picking", domain, ["id"], ["carrier_id"]);
  const rows: CarrierLoad[] = groups.map((g) => ({
    carrier: m2oName(g.carrier_id) ?? "Senza corriere",
    open: typeof g.__count === "number" ? g.__count : 0,
  }));
  return { rows };
});
