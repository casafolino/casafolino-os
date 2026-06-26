// GET /api/wb/shipments-today — spedizioni in partenza oggi, per corriere,
// + split pronti/da imballare + ordini in ritardo (per scena logistica).
// Scene: produzione, vetrina, logistica. Nessun campo importo.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { readGroup, searchCount, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface CarrierRow {
  carrier: string;
  count: number;
}
interface LateRow {
  partner: string;
  due: string | null;
}

const MOCK = {
  rows: [
    { carrier: "DHL Express", count: 3 },
    { carrier: "GLS", count: 2 },
    { carrier: "Ritiro cliente", count: 1 },
  ] as CarrierRow[],
  ready: 4,
  toPack: 2,
  lateRows: [{ partner: "Bella Italia NYC", due: "2026-06-24" }] as LateRow[],
};

export const GET = wbHandler("shipments-today", async () => {
  if (shouldUseMock()) {
    return { ...MOCK, total: MOCK.rows.reduce((s, r) => s + r.count, 0), late: MOCK.lateRows.length };
  }
  const today = todayISO();
  const todayDomain = [
    ["picking_type_code", "=", "outgoing"],
    ["scheduled_date", ">=", `${today} 00:00:00`],
    ["scheduled_date", "<=", `${today} 23:59:59`],
  ];
  const groups = await readGroup("stock.picking", todayDomain, ["id"], ["carrier_id"]);
  const rows: CarrierRow[] = groups.map((g) => ({
    carrier: m2oName(g.carrier_id) ?? "Senza corriere",
    count: typeof g.__count === "number" ? g.__count : 0,
  }));
  rows.sort((a, b) => b.count - a.count);

  // Split pronti (assigned) vs da imballare (confirmed/waiting) per oggi.
  const ready = await searchCount("stock.picking", [...todayDomain, ["state", "=", "assigned"]]);
  const toPack = await searchCount("stock.picking", [...todayDomain, ["state", "in", ["confirmed", "waiting"]]]);

  // In ritardo: outgoing scheduled < oggi, non spediti.
  const lateRecs = await searchRead<{ partner_id: unknown; scheduled_date: string | false }>(
    "stock.picking",
    [
      ["picking_type_code", "=", "outgoing"],
      ["scheduled_date", "<", `${today} 00:00:00`],
      ["state", "not in", ["done", "cancel"]],
    ],
    { fields: ["partner_id", "scheduled_date"], order: "scheduled_date asc", limit: 8 },
  );
  const lateRows: LateRow[] = lateRecs.map((r) => ({
    partner: m2oName(r.partner_id) ?? "Cliente",
    due: typeof r.scheduled_date === "string" ? r.scheduled_date.slice(0, 10) : null,
  }));

  return { rows, total: rows.reduce((s, r) => s + r.count, 0), ready, toPack, lateRows, late: lateRows.length };
});
