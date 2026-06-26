// GET /api/wb/production-queue — ordini da evadere, raggruppati per cliente.
// Scene: produzione, ufficio. MAI campi importo (€) nel payload.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { readGroup, m2oId, m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface QueueRow {
  partner: string;
  countryCode: string | null;
  country: string | null;
  colli: number;
  /** data evasione più vicina (ISO date) per priorità; null se assente. */
  due: string | null;
  /** true se la data più vicina è già passata (ordine in ritardo). */
  late: boolean;
}

// MOCK: una riga in ritardo (due ieri) per esercitare coda priorità + evidenza.
const MOCK: QueueRow[] = [
  { partner: "Bella Italia NYC", countryCode: "US", country: "Stati Uniti", colli: 6, due: "2026-06-24", late: true },
  { partner: "Gourmet Imports GmbH", countryCode: "DE", country: "Germania", colli: 4, due: "2026-06-25", late: false },
  { partner: "Nordic Deli AB", countryCode: "SE", country: "Svezia", colli: 3, due: "2026-06-26", late: false },
  { partner: "Maison du Goût", countryCode: "FR", country: "Francia", colli: 2, due: "2026-06-27", late: false },
  { partner: "Sapori Veri SL", countryCode: "ES", country: "Spagna", colli: 1, due: "2026-06-28", late: false },
];

/** Ordina per coda priorità: scadenza più vicina, poi ordine più grande. */
function byPriority(a: QueueRow, b: QueueRow): number {
  const da = a.due ?? "9999-12-31";
  const db = b.due ?? "9999-12-31";
  if (da !== db) return da < db ? -1 : 1;
  return b.colli - a.colli;
}

export const GET = wbHandler("production-queue", async () => {
  if (shouldUseMock()) {
    const rows = [...MOCK].sort(byPriority);
    return { rows, total: rows.reduce((s, r) => s + r.colli, 0), late: rows.filter((r) => r.late).length };
  }
  // Solo picking in uscita pronti/da preparare. Nessun campo importo letto.
  const domain = [
    ["picking_type_code", "=", "outgoing"],
    ["state", "in", ["assigned", "confirmed"]],
  ];
  // scheduled_date:min → scadenza più vicina per cliente (coda priorità).
  const groups = await readGroup("stock.picking", domain, ["scheduled_date:min"], ["partner_id"], {
    orderby: "partner_id",
  });
  const today = todayISO();
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
    const raw = typeof g.scheduled_date === "string" ? g.scheduled_date : null;
    const due = raw ? raw.slice(0, 10) : null;
    return {
      partner: m2oName(g.partner_id) ?? "Cliente",
      countryCode: c?.code ?? null,
      country: c?.name ?? null,
      colli: typeof g.__count === "number" ? g.__count : 0,
      due,
      late: due != null && due < today,
    };
  });
  rows.sort(byPriority);
  return { rows, total: rows.reduce((s, r) => s + r.colli, 0), late: rows.filter((r) => r.late).length };
});
