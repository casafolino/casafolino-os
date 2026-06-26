// GET /api/wb/daily-goal?dept=produzione|logistica — obiettivo del giorno + fatto.
// Scene: produzione, logistica, ufficio. Nessun campo importo.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock } from "@/lib/odoo";
import { searchCount } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

function dayBounds() {
  const t = todayISO();
  return { from: `${t} 00:00:00`, to: `${t} 23:59:59` };
}

export const GET = wbHandler("daily-goal", async ({ req }) => {
  const dept = new URL(req.url).searchParams.get("dept") === "logistica" ? "logistica" : "produzione";
  if (shouldUseMock()) {
    return dept === "logistica"
      ? { dept, label: "Spedizioni del giorno", done: 7, goal: 12, unit: "spedizioni" }
      : { dept, label: "Lotti del giorno", done: 4, goal: 9, unit: "lotti" };
  }
  const { from, to } = dayBounds();
  if (dept === "logistica") {
    const goal = await searchCount("stock.picking", [
      ["picking_type_code", "=", "outgoing"],
      ["scheduled_date", ">=", from],
      ["scheduled_date", "<=", to],
    ]);
    const done = await searchCount("stock.picking", [
      ["picking_type_code", "=", "outgoing"],
      ["scheduled_date", ">=", from],
      ["scheduled_date", "<=", to],
      ["state", "=", "done"],
    ]);
    return { dept, label: "Spedizioni del giorno", done, goal, unit: "spedizioni" };
  }
  // produzione: lotti pianificati oggi (date_start) vs completati oggi.
  const goal = await searchCount("mrp.production", [
    ["date_start", ">=", from],
    ["date_start", "<=", to],
  ]);
  const done = await searchCount("mrp.production", [
    ["date_start", ">=", from],
    ["date_start", "<=", to],
    ["state", "=", "done"],
  ]);
  return { dept, label: "Lotti del giorno", done, goal, unit: "lotti" };
});
