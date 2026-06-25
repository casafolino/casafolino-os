// GET /api/wb/certifications — badge certificazioni (config statica, nessuna query Odoo).
// Scene: vetrina.
import { wbHandler } from "@/lib/wb/handler";

export const dynamic = "force-dynamic";

const CERTS = ["BRC", "IFS", "Kosher", "Halal", "Bio"];

export const GET = wbHandler("certifications", async () => {
  return { certs: CERTS };
});
