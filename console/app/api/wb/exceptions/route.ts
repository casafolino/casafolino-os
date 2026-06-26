// GET /api/wb/exceptions — pannello eccezioni per la DIREZIONE.
// Aggrega SOLO gli item in stato warn/alert da tutte le aree. Scene: direzione, ufficio.
// Nessuna scrittura. Calcolo soglie server-side via lib/wb/thresholds + lib/wb/cutoffs.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { readGroup, searchCount, m2oName } from "@/lib/wb/odooWb";
import {
  type Status,
  lateOrdersStatus,
  qcBlocksStatus,
  notStartedLotsStatus,
  cutoffStatus,
  followupStatus,
  THRESHOLDS,
} from "@/lib/wb/thresholds";
import { cutoffFor, minutesToCutoff } from "@/lib/wb/cutoffs";

export const dynamic = "force-dynamic";

interface Exception {
  kind: string;
  label: string;
  detail: string;
  status: Status;
  count: number;
}

const RANK: Record<Status, number> = { ok: 0, warn: 1, alert: 2 };

function daysAgoISO(days: number): string {
  const d = new Date(`${todayISO()}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

const MOCK: Exception[] = [
  { kind: "late-orders", label: "Ordini in ritardo", detail: "3 spedizioni oltre la data", status: "alert", count: 3 },
  { kind: "cutoff", label: "Cut-off DHL a rischio", detail: "5 ordini aperti, ritiro tra 42 min", status: "warn", count: 5 },
  { kind: "followup", label: "Follow-up che si raffredda", detail: "2 lead post-fiera fermi da >7 giorni", status: "alert", count: 2 },
];

export const GET = wbHandler("exceptions", async ({ req }) => {
  const demo = new URL(req.url).searchParams.get("demo");
  if (shouldUseMock()) {
    if (demo === "calm") return { exceptions: [], summary: { lateOrders: 0, qcBlocks: 0, notStartedLots: 0 } };
    return {
      exceptions: [...MOCK].sort((a, b) => RANK[b.status] - RANK[a.status]),
      summary: { lateOrders: 3, qcBlocks: 0, notStartedLots: 1 },
    };
  }

  const today = todayISO();
  const out: Exception[] = [];

  // 1) Ordini in ritardo: outgoing scheduled < oggi, non spediti.
  const lateOrders = await searchCount("stock.picking", [
    ["picking_type_code", "=", "outgoing"],
    ["scheduled_date", "<", `${today} 00:00:00`],
    ["state", "not in", ["done", "cancel"]],
  ]);
  const lateSt = lateOrdersStatus(lateOrders);
  if (lateSt !== "ok") {
    out.push({ kind: "late-orders", label: "Ordini in ritardo", detail: `${lateOrders} spedizioni oltre la data`, status: lateSt, count: lateOrders });
  }

  // 2) QC bloccanti.
  const qc = await searchCount("cf.task", [
    ["state", "=", "in_corso"],
    ["traffic_light", "=", "red"],
  ]);
  const qcSt = qcBlocksStatus(qc);
  if (qcSt !== "ok") {
    out.push({ kind: "qc", label: "QC bloccanti", detail: `${qc} controlli da sbloccare`, status: qcSt, count: qc });
  }

  // 3) Lotti pianificati oggi non avviati.
  const notStarted = await searchCount("mrp.production", [
    ["date_start", ">=", `${today} 00:00:00`],
    ["date_start", "<=", `${today} 23:59:59`],
    ["state", "=", "confirmed"],
  ]);
  const nsSt = notStartedLotsStatus(notStarted);
  if (nsSt !== "ok") {
    out.push({ kind: "not-started", label: "Lotti non avviati", detail: `${notStarted} lotti pianificati oggi fermi`, status: nsSt, count: notStarted });
  }

  // 4) Cut-off a rischio (per corriere con orario configurato).
  const carrierGroups = await readGroup(
    "stock.picking",
    [
      ["picking_type_code", "=", "outgoing"],
      ["state", "not in", ["done", "cancel"]],
    ],
    ["id"],
    ["carrier_id"],
  );
  for (const g of carrierGroups) {
    const name = m2oName(g.carrier_id);
    const cfg = cutoffFor(name);
    const open = typeof g.__count === "number" ? g.__count : 0;
    if (!cfg || open <= 0) continue;
    const mins = minutesToCutoff(cfg.pickup);
    const st = cutoffStatus(mins, open);
    if (st !== "ok") {
      out.push({ kind: "cutoff", label: `Cut-off ${cfg.label} a rischio`, detail: `${open} ordini aperti, ritiro tra ${Math.max(0, mins)} min`, status: st, count: open });
    }
  }

  // 5) Follow-up post-fiera che si raffredda.
  const coolingFrom = daysAgoISO(THRESHOLDS.followupCooling.warnDays);
  const coolingLeads = await searchRead<{ id: number; name: string; write_date: string; cf_fair_id: unknown }>(
    "crm.lead",
    [
      ["type", "=", "opportunity"],
      ["cf_fair_id", "!=", false],
      ["write_date", "<", `${coolingFrom} 00:00:00`],
    ],
    { fields: ["name", "write_date", "cf_fair_id"], limit: 50, order: "write_date asc" },
  );
  if (coolingLeads.length) {
    let wst: Status = "warn";
    for (const l of coolingLeads) {
      const days = Math.floor((Date.now() - new Date(l.write_date).getTime()) / 86400000);
      if (RANK[followupStatus(days)] > RANK[wst]) wst = followupStatus(days);
    }
    out.push({ kind: "followup", label: "Follow-up che si raffredda", detail: `${coolingLeads.length} lead post-fiera fermi`, status: wst, count: coolingLeads.length });
  }

  out.sort((a, b) => RANK[b.status] - RANK[a.status]);
  return {
    exceptions: out,
    summary: { lateOrders, qcBlocks: qc, notStartedLots: notStarted },
  };
});
