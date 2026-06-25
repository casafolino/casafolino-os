// GET /api/wb/qc-blocks — controlli QC bloccanti (task rossi, instradati a Maria).
// Scene: produzione. 0 blocchi → stato verde; ≥1 → righe in alert.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { m2oId } from "@/lib/wb/odooWb";
import { nomeOperatore } from "@/lib/wb/operatori";

export const dynamic = "force-dynamic";

interface BlockRow {
  titolo: string;
  operatore: string;
}

export const GET = wbHandler("qc-blocks", async () => {
  if (shouldUseMock()) {
    // Default: nessun blocco → stato verde "tutto a posto".
    const rows: BlockRow[] = [];
    return { rows, blocked: rows.length };
  }
  const domain = [
    ["state", "=", "in_corso"],
    ["traffic_light", "=", "red"],
  ];
  const recs = await searchRead<{
    name: string;
    bo_operatore_id: unknown;
    bo_titolare_id: unknown;
  }>("cf.task", domain, {
    fields: ["name", "bo_operatore_id", "bo_titolare_id"],
    order: "write_date desc",
    limit: 20,
  });
  const rows: BlockRow[] = recs.map((r) => ({
    titolo: r.name,
    operatore: nomeOperatore(m2oId(r.bo_operatore_id) ?? m2oId(r.bo_titolare_id)),
  }));
  return { rows, blocked: rows.length };
});
