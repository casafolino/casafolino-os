"use client";
// Guscio comune di un tile: header + corpo + gestione stato loading/errore.
import type { ReactNode } from "react";
import type { PollState } from "./usePoll";

export type Tint = "" | "sage" | "blush" | "sky" | "butter" | "clay";

export function TileShell({
  title,
  right,
  tint = "",
  span,
  rowSpan,
  children,
}: {
  title: string;
  right?: ReactNode;
  tint?: Tint;
  span?: number;
  rowSpan?: number;
  children: ReactNode;
}) {
  const style: React.CSSProperties = {};
  if (span) style.gridColumn = `span ${span}`;
  if (rowSpan) style.gridRow = `span ${rowSpan}`;
  return (
    <section className={`wb-tile${tint ? ` tint-${tint}` : ""}`} style={style}>
      <div className="wb-tile-h">
        <span>{title}</span>
        {right}
      </div>
      <div className="wb-tile-body">{children}</div>
    </section>
  );
}

/** Render condizionale dello stato di un poll: mostra loading/errore o il contenuto. */
export function PollBody<T>({
  state,
  children,
  emptyWhen,
  emptyLabel = "Nessun dato",
}: {
  state: PollState<T>;
  children: (data: T) => ReactNode;
  emptyWhen?: (data: T) => boolean;
  emptyLabel?: string;
}) {
  if (state.error) return <div className="wb-state err">⚠ {state.error}</div>;
  if (state.loading && !state.data) return <div className="wb-state">Carico…</div>;
  if (!state.data) return <div className="wb-state">{emptyLabel}</div>;
  if (emptyWhen && emptyWhen(state.data)) return <div className="wb-state">{emptyLabel}</div>;
  return <>{children(state.data)}</>;
}
