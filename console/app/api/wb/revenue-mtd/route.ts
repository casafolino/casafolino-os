// GET /api/wb/revenue-mtd — fatturato mese in corso + delta vs target/mese precedente.
// Scene: SOLO vetrina, ufficio (production → 403 dalla guardia scope).
//
// Esposizione della CIFRA assoluta:
//  - scope ufficio: cifra sempre visibile (back office interno).
//  - scope vetrina: cifra esposta SOLO se SHOW_REVENUE_FIGURE=true; default false →
//    si mostra solo la % di crescita (buyer non vedono il fatturato secco).
import { wbHandler, firstOfMonthISO } from "@/lib/wb/handler";
import { shouldUseMock, getConfigParam } from "@/lib/odoo";
import { readGroup } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

const SHOW_FIGURE = process.env.SHOW_REVENUE_FIGURE === "true";

function prevMonthRange(now = new Date()): { start: string; end: string } {
  const y = now.getUTCFullYear();
  const m = now.getUTCMonth(); // 0-based, mese corrente
  const start = new Date(Date.UTC(y, m - 1, 1));
  const end = new Date(Date.UTC(y, m, 1)); // primo del mese corrente (esclusivo)
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

async function sumInvoiced(fromISO: string, toExclusiveISO?: string): Promise<number> {
  const domain: unknown[] = [
    ["move_type", "=", "out_invoice"],
    ["state", "=", "posted"],
    ["invoice_date", ">=", fromISO],
  ];
  if (toExclusiveISO) domain.push(["invoice_date", "<", toExclusiveISO]);
  const groups = await readGroup("account.move", domain, ["amount_total:sum"], []);
  const row = groups[0] as { amount_total?: number } | undefined;
  return row?.amount_total ?? 0;
}

export const GET = wbHandler("revenue-mtd", async ({ scope }) => {
  let amount: number;
  let prev: number;
  let target = 0;
  if (shouldUseMock()) {
    amount = 48200;
    prev = 41000;
    target = 50000;
  } else {
    amount = await sumInvoiced(firstOfMonthISO());
    const pm = prevMonthRange();
    prev = await sumInvoiced(pm.start, pm.end);
    const tParam = await getConfigParam("casafolino.wb_revenue_target");
    target = tParam ? Number(tParam) || 0 : 0;
  }
  const growthPct = prev > 0 ? Math.round(((amount - prev) / prev) * 100) : null;
  const targetPct = target > 0 ? Math.round((amount / target) * 100) : null;

  // Esposizione cifra: ufficio sempre, vetrina solo se flag attivo.
  const exposeFigure = scope === "ufficio" || SHOW_FIGURE;
  return {
    ...(exposeFigure ? { amount, target } : {}),
    growthPct,
    targetPct,
    figureVisible: exposeFigure,
  };
});
