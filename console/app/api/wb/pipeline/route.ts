// GET /api/wb/pipeline — pipeline CRM per stage + follow-up scaduti.
// Scene: SOLO ufficio (ogni altro scope → 403 dalla guardia).
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock } from "@/lib/odoo";
import { readGroup, searchCount, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface StageRow {
  stage: string;
  count: number;
  expected: number;
}

const MOCK: StageRow[] = [
  { stage: "Nuovo", count: 8, expected: 32000 },
  { stage: "Qualificato", count: 5, expected: 58000 },
  { stage: "Proposta", count: 3, expected: 91000 },
  { stage: "Negoziazione", count: 2, expected: 120000 },
];

export const GET = wbHandler("pipeline", async () => {
  if (shouldUseMock()) {
    return { rows: MOCK, overdue: 4, totalExpected: MOCK.reduce((s, r) => s + r.expected, 0) };
  }
  const domain = [["type", "=", "opportunity"]];
  const groups = await readGroup(
    "crm.lead",
    domain,
    ["expected_revenue:sum"],
    ["stage_id"],
    { orderby: "stage_id" },
  );
  const rows: StageRow[] = groups.map((g) => ({
    stage: m2oName(g.stage_id) ?? "—",
    count: typeof g.__count === "number" ? g.__count : 0,
    expected: typeof g.expected_revenue === "number" ? g.expected_revenue : 0,
  }));
  const overdue = await searchCount("crm.lead", [
    ["type", "=", "opportunity"],
    ["activity_date_deadline", "<", todayISO()],
  ]);
  return { rows, overdue, totalExpected: rows.reduce((s, r) => s + r.expected, 0) };
});
