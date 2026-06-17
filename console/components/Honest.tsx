// no-trattino: mai "—". Ogni campo è dato reale o vuoto-onesto-con-azione.
import type { ReactNode } from "react";

/** Vuoto onesto: spiega cosa manca e offre un'azione (mai un trattino). */
export function EmptyHonest({ label, actionLabel }: { label: string; actionLabel?: string }) {
  return (
    <div className="empty-honest">
      <span>{label}</span>
      {actionLabel ? <span className="empty-action">{actionLabel}</span> : null}
    </div>
  );
}

/** Mostra il valore se presente, altrimenti un fallback onesto (testo, non "—"). */
export function orHonest(value: ReactNode, fallback: string): ReactNode {
  if (value === null || value === undefined || value === "" ) return <span style={{ color: "var(--muted)" }}>{fallback}</span>;
  return value;
}

export function money(amount: number | null | undefined, currency = "EUR"): string {
  if (amount === null || amount === undefined) return "non disponibile";
  try {
    return new Intl.NumberFormat("it-IT", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${amount} ${currency}`;
  }
}

export function dateLabel(iso: string | null | undefined): string {
  if (!iso) return "senza data";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "senza data";
  return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}
