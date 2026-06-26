// Orari di ritiro corrieri — NON sono in Odoo. Config client-side, Antonio corregge.
// Il countdown è calcolato lato client, indipendente da Odoo.
export interface Cutoff {
  /** chiave di match su carrier_id name (case-insensitive, substring). */
  match: string;
  label: string;
  /** orario ritiro "HH:MM" (timezone locale del monitor). */
  pickup: string;
}

// PLACEHOLDER — valori reali da confermare con Antonio.
export const CUTOFFS: Cutoff[] = [
  { match: "dhl", label: "DHL", pickup: "16:00" },
  { match: "gls", label: "GLS", pickup: "15:30" },
  { match: "brt", label: "BRT", pickup: "16:30" },
];

/** Risolve la config cut-off dal nome corriere Odoo. */
export function cutoffFor(carrierName: string | null | undefined): Cutoff | null {
  const n = (carrierName ?? "").toLowerCase();
  return CUTOFFS.find((c) => n.includes(c.match)) ?? null;
}

/** Minuti rimanenti al cut-off "HH:MM" rispetto a `now` (negativo se passato). */
export function minutesToCutoff(pickup: string, now = new Date()): number {
  const [h, m] = pickup.split(":").map((x) => parseInt(x, 10));
  const target = new Date(now);
  target.setHours(h, m, 0, 0);
  return Math.round((target.getTime() - now.getTime()) / 60000);
}

/** "HH:MM" rimanente da minuti (clamp a 0). */
export function fmtCountdown(minutesLeft: number): string {
  const mins = Math.max(0, minutesLeft);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}
