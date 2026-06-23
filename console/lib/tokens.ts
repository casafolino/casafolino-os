// F0 — Design tokens (mirror TS dei CSS vars in app/globals.css, console_reference_v4).
// Single source per i componenti TS/React: niente colori hardcoded sparsi.
// I valori puntano alle CSS var dove possibile (tema coerente, un solo punto di verità nel CSS).

/** Token colore come riferimento a CSS var (usabili in style={{...}}). */
export const t = {
  canvas: "var(--canvas)",
  paper: "var(--paper)",
  panel: "var(--panel)",
  panel2: "var(--panel-2)",
  ink: "var(--ink)",
  muted: "var(--muted)",
  faint: "var(--faint)",
  line: "var(--line)",
  line2: "var(--line-2)",
  accent: "var(--accent)",
  accentT: "var(--accent-t)",
  ok: "var(--ok)",
  okT: "var(--ok-t)",
  warn: "var(--warn)",
  warnT: "var(--warn-t)",
  danger: "var(--danger)",
  dangerT: "var(--danger-t)",
  rSm: "var(--r-sm)",
  rMd: "var(--r-md)",
  rLg: "var(--r-lg)",
} as const;

/** Tono semantico → coppia testo/sfondo (per Pill, badge, chip di stato). */
export type Tone = "neutral" | "info" | "success" | "warning" | "danger";
export const toneStyle: Record<Tone, { fg: string; bg: string }> = {
  neutral: { fg: t.muted, bg: t.panel2 },
  info: { fg: t.accent, bg: t.accentT },
  success: { fg: t.ok, bg: t.okT },
  warning: { fg: t.warn, bg: t.warnT },
  danger: { fg: t.danger, bg: t.dangerT },
};

/** Stato attività/rotting (reale) → tono. neutral = nessuna attività (mai rosso falso). */
export const activityTone: Record<string, Tone> = {
  fresh: "success",
  warning: "warning",
  danger: "danger",
  neutral: "neutral",
};

/** Urgenza prossima azione da data ISO → tono + etichetta (scaduta / imminente / futura). */
export function actionUrgency(
  iso: string | null | undefined,
  now: number = Date.now()
): { tone: Tone; label: string } | null {
  if (!iso) return null;
  const d = new Date(iso).getTime();
  if (isNaN(d)) return null;
  const days = Math.floor((d - now) / 86400000);
  if (days < 0) return { tone: "danger", label: "scaduta" };
  if (days === 0) return { tone: "warning", label: "oggi" };
  if (days <= 3) return { tone: "warning", label: `tra ${days}g` };
  return null;
}

/** Colore deterministico da stringa (avatar fallback) — palette categoriale stabile. */
const CATEGORICAL = [
  "#3F8A4F", "#8B5CF6", "#8A5A1E", "#2E6BB8", "#1D8A66", "#9A6B1E", "#7A4FA3", "#3E7C8C",
];
export function colorFor(seed: string | null | undefined): string {
  const s = (seed || "").trim();
  if (!s) return "var(--op-other)";
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return CATEGORICAL[h % CATEGORICAL.length];
}

export function initials(name: string | null | undefined): string {
  return (
    (name || "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("") || "·"
  );
}
