// GET /api/wb/ticker — feed eventi recenti (ordini/lotti/spedizioni/fiere).
// Scene: vetrina, ufficio. Senza importi (i nuovi ordini scorrono senza valore €).
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

interface TickerItem {
  icon: "order" | "lot" | "ship" | "fair";
  text: string;
}

const MOCK: TickerItem[] = [
  { icon: "order", text: "Nuovo ordine — Gourmet Imports GmbH (DE)" },
  { icon: "lot", text: "Lotto completato — Nduja artigianale 200g" },
  { icon: "ship", text: "Spedizione partita — DHL → Stati Uniti" },
  { icon: "fair", text: "Anuga 2026 tra 82 giorni" },
  { icon: "order", text: "Nuovo ordine — Nordic Deli AB (SE)" },
];

export const GET = wbHandler("ticker", async () => {
  if (shouldUseMock()) return { items: MOCK };
  const today = todayISO();
  const items: TickerItem[] = [];

  // Spedizioni partite oggi (done outgoing).
  const ships = await searchRead<{ partner_id: unknown; carrier_id: unknown }>(
    "stock.picking",
    [
      ["picking_type_code", "=", "outgoing"],
      ["state", "=", "done"],
      ["date_done", ">=", `${today} 00:00:00`],
    ],
    { fields: ["partner_id", "carrier_id"], order: "date_done desc", limit: 5 },
  );
  for (const s of ships) {
    items.push({
      icon: "ship",
      text: `Spedizione partita — ${m2oName(s.carrier_id) ?? "corriere"} → ${m2oName(s.partner_id) ?? "cliente"}`,
    });
  }

  // Lotti / produzioni completate di recente (NO importi).
  const lots = await searchRead<{ name: string; product_id: unknown }>(
    "mrp.production",
    [["state", "=", "done"]],
    { fields: ["name", "product_id"], order: "date_finished desc", limit: 5 },
  );
  for (const l of lots) {
    items.push({ icon: "lot", text: `Lotto completato — ${m2oName(l.product_id) ?? l.name}` });
  }

  // Prossima fiera.
  const fairs = await searchRead<{ name: string; date_start: string | false }>(
    "cf.export.fair",
    [["date_start", ">=", today]],
    { fields: ["name", "date_start"], order: "date_start asc", limit: 1 },
  );
  if (fairs.length && typeof fairs[0].date_start === "string") {
    const days = Math.round(
      (new Date(`${fairs[0].date_start}T00:00:00Z`).getTime() -
        new Date(`${today}T00:00:00Z`).getTime()) /
        86400000,
    );
    items.push({ icon: "fair", text: `${fairs[0].name} tra ${days} giorni` });
  }

  return { items: items.length ? items : MOCK };
});
