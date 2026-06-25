// GET /api/wb/production-queue — ordini da evadere, raggruppati per cliente.
// Scene: produzione, ufficio. MAI campi importo (€) nel payload.
import { wbHandler } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { readGroup, m2oId, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface QueueRow {
  partner: string;
  countryCode: string | null;
  country: string | null;
  colli: number;
}

const MOCK: QueueRow[] = [
  { partner: "Gourmet Imports GmbH", countryCode: "DE", country: "Germania", colli: 4 },
  { partner: "Maison du Goût", countryCode: "FR", country: "Francia", colli: 2 },
  { partner: "Nordic Deli AB", countryCode: "SE", country: "Svezia", colli: 3 },
  { partner: "Bella Italia NYC", countryCode: "US", country: "Stati Uniti", colli: 6 },
  { partner: "Sapori Veri SL", countryCode: "ES", country: "Spagna", colli: 1 },
];

export const GET = wbHandler("production-queue", async () => {
  if (shouldUseMock()) {
    return { rows: MOCK, total: MOCK.reduce((s, r) => s + r.colli, 0) };
  }
  // Solo picking in uscita pronti/da preparare. Nessun campo importo letto.
  const domain = [
    ["picking_type_code", "=", "outgoing"],
    ["state", "in", ["assigned", "confirmed"]],
  ];
  const groups = await readGroup("stock.picking", domain, ["id"], ["partner_id"], {
    orderby: "partner_id",
  });
  const partnerIds = groups.map((g) => m2oId(g.partner_id)).filter((x): x is number => x != null);
  // country_id vive su res.partner (granted al gruppo console_api).
  const partners = partnerIds.length
    ? await searchRead<{ id: number; country_id: unknown }>("res.partner", [["id", "in", partnerIds]], {
        fields: ["id", "country_id"],
      })
    : [];
  const countryById = new Map<number, { code: string | null; name: string | null }>();
  // country_id m2o → poi risolviamo il codice ISO via res.country.
  const countryIds = Array.from(
    new Set(partners.map((p) => m2oId(p.country_id)).filter((x): x is number => x != null)),
  );
  const countries = countryIds.length
    ? await searchRead<{ id: number; code: string }>("res.country", [["id", "in", countryIds]], {
        fields: ["id", "code"],
      })
    : [];
  const codeById = new Map(countries.map((c) => [c.id, c.code]));
  for (const p of partners) {
    const cid = m2oId(p.country_id);
    countryById.set(p.id, {
      code: cid ? codeById.get(cid) ?? null : null,
      name: m2oName(p.country_id),
    });
  }
  const rows: QueueRow[] = groups.map((g) => {
    const pid = m2oId(g.partner_id);
    const c = pid ? countryById.get(pid) : undefined;
    return {
      partner: m2oName(g.partner_id) ?? "Cliente",
      countryCode: c?.code ?? null,
      country: c?.name ?? null,
      colli: typeof g.__count === "number" ? g.__count : 0,
    };
  });
  rows.sort((a, b) => b.colli - a.colli);
  return { rows, total: rows.reduce((s, r) => s + r.colli, 0) };
});
