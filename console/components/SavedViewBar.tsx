"use client";
// F3 — Barra viste salvate, riusabile cross-surface. La scelta persiste per utente (localStorage,
// chiave passata dal chiamante). Presentazionale: il filtro effettivo lo applica il consumatore.
import { useEffect, useState } from "react";

export type SavedView = { key: string; label: string };

export function useSavedView(storageKey: string, fallback: string): [string, (v: string) => void] {
  const [view, setView] = useState(fallback);
  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) setView(saved);
  }, [storageKey]);
  function set(v: string) {
    setView(v);
    localStorage.setItem(storageKey, v);
  }
  return [view, set];
}

export function SavedViewBar({
  views,
  active,
  onChange,
}: {
  views: SavedView[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
      {views.map((v) => (
        <button
          key={v.key}
          className="btn-mini"
          onClick={() => onChange(v.key)}
          style={active === v.key ? { background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" } : undefined}
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}
