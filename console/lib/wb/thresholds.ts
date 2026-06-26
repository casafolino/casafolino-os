// Soglie semaforiche del wallboard — UNICA fonte. Niente soglie hardcoded nei tile.
// Antonio tara questi valori; i tile leggono solo lo status calcolato qui.
export type Status = "ok" | "warn" | "alert";

/** Sceglie il "peggiore" tra più status (per aggregare un pannello). */
export function worst(...s: Status[]): Status {
  const rank: Record<Status, number> = { ok: 0, warn: 1, alert: 2 };
  return s.reduce<Status>((acc, x) => (rank[x] > rank[acc] ? x : acc), "ok");
}

export const THRESHOLDS = {
  // Ordini in ritardo: scheduled_date < oggi e non spediti.
  lateOrders: { warnAt: 1, alertAt: 3 }, // n. ordini in ritardo
  // Cut-off corriere a rischio: minuti rimanenti con ordini ancora aperti.
  // Finestra volutamente stretta: ordini piccoli (1-2 pezzi) si chiudono in pochi minuti.
  cutoff: { warnMin: 30, alertMin: 10 },
  // Follow-up post-fiera che si raffredda: giorni dall'ultimo contatto.
  // Brief cut-off (2c): valore atteso warn 3 / alert 7 (V2 era warn 5 → allineato).
  followupCooling: { warnDays: 3, alertDays: 7 },
  // QC bloccanti presenti.
  qcBlocks: { alertAt: 1 },
  // Lotti pianificati oggi ma non avviati (entro fine mattina ~ metà giornata).
  notStartedLots: { warnAt: 1, alertAt: 3 },
} as const;

/** n. elementi → status su scala warn/alert (0 = ok). */
function byCount(n: number, warnAt: number, alertAt: number): Status {
  if (n >= alertAt) return "alert";
  if (n >= warnAt) return "warn";
  return "ok";
}

export function lateOrdersStatus(n: number): Status {
  return byCount(n, THRESHOLDS.lateOrders.warnAt, THRESHOLDS.lateOrders.alertAt);
}

export function qcBlocksStatus(n: number): Status {
  return n >= THRESHOLDS.qcBlocks.alertAt ? "alert" : "ok";
}

export function notStartedLotsStatus(n: number): Status {
  return byCount(n, THRESHOLDS.notStartedLots.warnAt, THRESHOLDS.notStartedLots.alertAt);
}

/**
 * Cut-off: minuti rimanenti + ordini ancora aperti per quel corriere.
 * - 0 ordini da chiudere → neutro (anche dentro la finestra: niente allarme inutile).
 * - ritiro già passato (minutesLeft < 0) → neutro (no rumore dalle 13 alle 18).
 * - altrimenti: < alertMin → alert, < warnMin → warn (soglie strette).
 */
export function cutoffStatus(minutesLeft: number, openOrders: number): Status {
  if (openOrders <= 0) return "ok";
  if (minutesLeft < 0) return "ok"; // ritiro odierno completato
  if (minutesLeft < THRESHOLDS.cutoff.alertMin) return "alert";
  if (minutesLeft < THRESHOLDS.cutoff.warnMin) return "warn";
  return "ok";
}

/** Follow-up: giorni dall'ultimo contatto. */
export function followupStatus(daysSinceContact: number): Status {
  if (daysSinceContact >= THRESHOLDS.followupCooling.alertDays) return "alert";
  if (daysSinceContact >= THRESHOLDS.followupCooling.warnDays) return "warn";
  return "ok";
}

/**
 * Pacing obiettivo giornaliero: confronta il fatto col ritmo atteso a quest'ora.
 * Atteso = obiettivo * (frazione di giornata lavorativa trascorsa). Tolleranza 15%.
 * @param fractionOfDay 0..1 — quanto della giornata lavorativa è passato
 */
export function pacingStatus(done: number, goal: number, fractionOfDay: number): Status {
  if (goal <= 0) return "ok";
  const expected = goal * Math.min(1, Math.max(0, fractionOfDay));
  if (done >= goal) return "ok";
  if (done >= expected * 0.85) return "ok";
  if (done >= expected * 0.6) return "warn";
  return "alert";
}

/** Frazione di giornata lavorativa trascorsa (default 08:00–18:00), client-side. */
export function workdayFraction(now = new Date(), startHour = 8, endHour = 18): number {
  const h = now.getHours() + now.getMinutes() / 60;
  if (h <= startHour) return 0;
  if (h >= endHour) return 1;
  return (h - startHour) / (endHour - startHour);
}

/** Mappa status → classe pill UI (vuota per ok = nessun colore d'allarme). */
export function pillClass(s: Status): string {
  return s === "alert" ? "alert" : s === "warn" ? "warn" : "ok";
}
