// F0 — Atomi Design System riusabili dai tre surface. Niente nuova libreria UI:
// solo React + i token (lib/tokens.ts) + le classi base di globals.css.
// Regole brief: superfici flat, bordi 0.5px, niente ombre/gradienti decorativi,
// sentence case, colore solo per significato.
"use client";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { t, toneStyle, colorFor, initials, type Tone } from "@/lib/tokens";
import { moneyCompact } from "@/components/Honest";

/** Pill semantica (ex .chip): tono → colori, opzionale dot. */
export function Pill({
  tone = "info",
  dot,
  children,
  title,
  style,
}: {
  tone?: Tone;
  dot?: boolean;
  children: ReactNode;
  title?: string;
  style?: React.CSSProperties;
}) {
  const s = toneStyle[tone];
  return (
    <span className="chip" title={title} style={{ background: s.bg, color: s.fg, ...style }}>
      {dot ? (
        <span style={{ width: 6, height: 6, borderRadius: 999, background: s.fg, display: "inline-block" }} />
      ) : null}
      {children}
    </span>
  );
}

/** Avatar a iniziali con colore deterministico (o colore esplicito). */
export function Avatar({
  name,
  color,
  size = 28,
  title,
}: {
  name: string | null | undefined;
  color?: string;
  size?: number;
  title?: string;
}) {
  const bg = color ?? colorFor(name);
  return (
    <span
      title={title ?? name ?? undefined}
      style={{
        width: size,
        height: size,
        borderRadius: 999,
        background: bg,
        color: "#fff",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 600,
        fontSize: Math.round(size * 0.4),
        flexShrink: 0,
      }}
    >
      {initials(name)}
    </span>
  );
}

/** Importo formattato compatto (€58k). Wrapper su moneyCompact per uso DS. */
export function Money({ value, style }: { value: number | null | undefined; style?: React.CSSProperties }) {
  return <span style={style}>{moneyCompact(value)}</span>;
}

/** Card di contesto per il right-rail: titolo (+ azione opz.) e corpo. */
export function RailCard({
  title,
  action,
  children,
  count,
}: {
  title: string;
  action?: ReactNode;
  count?: number;
  children: ReactNode;
}) {
  return (
    <div className="card" style={{ padding: 14 }}>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 9 }}>
        <span className="sec-title" style={{ margin: 0 }}>
          {title}
          {count != null ? <span className="muted" style={{ fontWeight: 400, marginLeft: 6 }}>{count}</span> : null}
        </span>
        {action ?? null}
      </div>
      {children}
    </div>
  );
}

/** Toast effimero (auto-dismiss). tone success/danger/info. */
export function Toast({
  message,
  tone = "info",
  onDismiss,
  ms = 3200,
}: {
  message: string;
  tone?: Tone;
  onDismiss: () => void;
  ms?: number;
}) {
  useEffect(() => {
    const id = setTimeout(onDismiss, ms);
    return () => clearTimeout(id);
  }, [onDismiss, ms]);
  const s = toneStyle[tone];
  return (
    <div
      onClick={onDismiss}
      role="status"
      style={{
        position: "fixed",
        bottom: 18,
        right: 18,
        zIndex: 60,
        background: s.bg,
        color: s.fg,
        border: `1px solid ${s.fg}`,
        borderRadius: t.rMd,
        padding: "9px 14px",
        fontSize: 13,
        fontWeight: 600,
        cursor: "pointer",
        maxWidth: 360,
      }}
    >
      {message}
    </div>
  );
}

export type InlineOption = { value: string; label: string };

/**
 * Campo a modifica inline (no modale): click sul valore → input/select in place →
 * Invio o blur salva, Esc annulla. Il salvataggio è delegato a onSave(value):
 * il chiamante fa il write ottimistico + rollback + toast. Se non editabile,
 * mostra solo il valore. Sentence case, bordi 0.5px, colore solo per significato.
 */
export function InlineEditField({
  value,
  display,
  editable = true,
  type = "text",
  options,
  placeholder,
  onSave,
  valueStyle,
}: {
  value: string;
  display?: ReactNode;
  editable?: boolean;
  type?: "text" | "number" | "select" | "date" | "email";
  options?: InlineOption[];
  placeholder?: string;
  onSave: (next: string) => Promise<boolean> | boolean;
  valueStyle?: React.CSSProperties;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement | null>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value);
      inputRef.current?.focus();
    }
  }, [editing, value]);

  async function commit() {
    if (busy) return;
    if (draft === value) {
      setEditing(false);
      return;
    }
    setBusy(true);
    const ok = await onSave(draft);
    setBusy(false);
    if (ok) setEditing(false);
  }
  function cancel() {
    setDraft(value);
    setEditing(false);
  }

  if (!editable) {
    return <span style={valueStyle}>{display ?? value ?? placeholder}</span>;
  }

  if (!editing) {
    const empty = value === "" || value == null;
    return (
      <span
        onClick={() => setEditing(true)}
        title="Clic per modificare"
        style={{
          cursor: "text",
          borderBottom: "1px dashed var(--line-2)",
          paddingBottom: 1,
          color: empty ? "var(--muted)" : undefined,
          ...valueStyle,
        }}
      >
        {empty ? placeholder ?? "imposta" : display ?? value}
      </span>
    );
  }

  const common = {
    ref: inputRef as never,
    value: draft,
    disabled: busy,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setDraft(e.target.value),
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && type !== "select") commit();
      if (e.key === "Escape") cancel();
    },
    onBlur: commit,
    style: {
      fontSize: "inherit",
      fontWeight: "inherit" as const,
      padding: "2px 6px",
      borderRadius: t.rSm,
      border: "1px solid var(--accent)",
      maxWidth: "100%",
    },
  };

  if (type === "select") {
    return (
      <select {...common}>
        {(options ?? []).map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    );
  }
  return <input {...common} type={type} placeholder={placeholder} />;
}
