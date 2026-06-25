// GET /api/wb/next-fair — prossima fiera da cf.export.fair, con countdown giorni.
// Scene: vetrina, ufficio.
import { wbHandler, todayISO } from "@/lib/wb/handler";
import { shouldUseMock, searchRead } from "@/lib/odoo";
import { m2oName } from "@/lib/wb/odooWb";

export const dynamic = "force-dynamic";

function daysUntil(iso: string): number {
  const d = new Date(`${iso}T00:00:00Z`).getTime();
  const now = new Date(`${todayISO()}T00:00:00Z`).getTime();
  return Math.round((d - now) / 86400000);
}

export const GET = wbHandler("next-fair", async () => {
  if (shouldUseMock()) {
    const date = "2026-09-15";
    return { name: "Anuga 2026", location: "Colonia", country: "Germania", date, days: daysUntil(date) };
  }
  const today = todayISO();
  const recs = await searchRead<{
    name: string;
    date_start: string | false;
    location: string | false;
    country_id: unknown;
  }>("cf.export.fair", [["date_start", ">=", today]], {
    fields: ["name", "date_start", "location", "country_id"],
    order: "date_start asc",
    limit: 1,
  });
  if (!recs.length) return { name: null };
  const f = recs[0];
  const date = typeof f.date_start === "string" ? f.date_start : null;
  return {
    name: f.name,
    location: f.location || null,
    country: m2oName(f.country_id),
    date,
    days: date ? daysUntil(date) : null,
  };
});
