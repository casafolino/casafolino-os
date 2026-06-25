// GET /api/wb/tasks-today — lavorazioni di oggi: operatore → mansione → stato.
// Scene: produzione. Mappa employee 9/6/3/10 → Maria/Teresa/Anna/Valentina.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { m2oId } from "@/lib/wb/odooWb";
import { nomeOperatore } from "@/lib/wb/operatori";

export const dynamic = "force-dynamic";

const KIND_LABEL: Record<string, string> = {
  produzione: "Produzione",
  campionatura: "Campionatura",
  ordine: "Ordine",
  generico: "Generico",
};

interface TaskRow {
  operatore: string;
  mansione: string;
  titolo: string;
  light: "green" | "yellow" | "red";
  qcOk: boolean;
}

const MOCK: TaskRow[] = [
  { operatore: "Maria", mansione: "Produzione", titolo: "Nduja — impasto lotto 231", light: "green", qcOk: true },
  { operatore: "Teresa", mansione: "Campionatura", titolo: "Kit buyer Vancouver", light: "yellow", qcOk: false },
  { operatore: "Anna", mansione: "Ordine", titolo: "Picking Gourmet Imports", light: "green", qcOk: true },
  { operatore: "Valentina", mansione: "Produzione", titolo: "Confezionamento olio EVO", light: "green", qcOk: true },
];

export const GET = wbHandler("tasks-today", async () => {
  if (shouldUseMock()) return { rows: MOCK };
  const domain = [["state", "=", "in_corso"]];
  const recs = await searchRead<{
    name: string;
    bo_kind: string | false;
    traffic_light: string | false;
    bo_titolare_id: unknown;
    bo_operatore_id: unknown;
  }>("cf.task", domain, {
    fields: ["name", "bo_kind", "traffic_light", "bo_titolare_id", "bo_operatore_id"],
    order: "write_date desc",
    limit: 40,
  });
  const rows: TaskRow[] = recs.map((r) => {
    const empId = m2oId(r.bo_operatore_id) ?? m2oId(r.bo_titolare_id);
    const light = (r.traffic_light || "green") as TaskRow["light"];
    return {
      operatore: nomeOperatore(empId),
      mansione: r.bo_kind ? KIND_LABEL[r.bo_kind] ?? r.bo_kind : "—",
      titolo: r.name,
      light,
      qcOk: light === "green",
    };
  });
  return { rows };
});
