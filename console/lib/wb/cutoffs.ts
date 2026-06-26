// Orari di ritiro corrieri — NON sono in Odoo. Config client-side, Antonio corregge.
// Il countdown è calcolato lato client, indipendente da Odoo.
export interface Cutoff {
  /** chiave di match su carrier_id name (case-insensitive, substring). */
  match: string;
  label: string;
  /** orario ritiro "HH:MM" (timezone locale del monitor). */
  pickup: string;
}

// CasaFolino: UN SOLO passaggio di ritiro giornaliero alle 13:00, condiviso da tutti i
// corrieri. Manteniamo la struttura per-corriere (interfaccia CutoffTile invariata), ma
// l'orario è identico per tutti.
export const COMPANY_PICKUP = "13:00";
export const CUTOFFS: Cutoff[] = [
  { match: "dhl", label: "DHL", pickup: COMPANY_PICKUP },
  { match: "gls", label: "GLS", pickup: COMPANY_PICKUP },
  { match: "brt", label: "BRT", pickup: COMPANY_PICKUP },
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

export interface PickupInfo {
  /** minuti al ritiro di OGGI (negativo se già passato). */
  minsToday: number;
  /** true se il ritiro di oggi è già passato. */
  passedToday: boolean;
  /** minuti al PROSSIMO ritiro (oggi se non passato, altrimenti domani). */
  minsNext: number;
}

/** Info ritiro: oggi vs prossimo (rollover a domani dopo il cut-off). */
export function pickupInfo(pickup: string, now = new Date()): PickupInfo {
  const minsToday = minutesToCutoff(pickup, now);
  const passedToday = minsToday < 0;
  if (!passedToday) return { minsToday, passedToday, minsNext: minsToday };
  const [h, m] = pickup.split(":").map((x) => parseInt(x, 10));
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(h, m, 0, 0);
  const minsNext = Math.round((tomorrow.getTime() - now.getTime()) / 60000);
  return { minsToday, passedToday, minsNext };
}

/** "HH:MM" rimanente da minuti (clamp a 0). */
export function fmtCountdown(minutesLeft: number): string {
  const mins = Math.max(0, minutesLeft);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}
