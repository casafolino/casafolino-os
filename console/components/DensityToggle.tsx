"use client";
// F3 — Densità compatto/comodo, persistita per utente (localStorage). Applica data-density
// su <html>; le regole in globals.css scalano spaziature e tipografia (effetto cross-surface).
import { useEffect, useState } from "react";

const KEY = "cf.console.density";
type Density = "comfortable" | "compact";

function apply(d: Density) {
  if (typeof document !== "undefined") document.documentElement.dataset.density = d;
}

/** Montato nel layout: applica la densità salvata prima del primo paint utile. */
export function DensityInit() {
  useEffect(() => {
    const saved = (typeof localStorage !== "undefined" && localStorage.getItem(KEY)) as Density | null;
    apply(saved === "compact" ? "compact" : "comfortable");
  }, []);
  return null;
}

/** Toggle riusabile (es. in Sidebar). */
export function DensityToggle() {
  const [density, setDensity] = useState<Density>("comfortable");
  useEffect(() => {
    const saved = (localStorage.getItem(KEY) as Density | null) ?? "comfortable";
    setDensity(saved);
    apply(saved);
  }, []);
  function toggle() {
    const next: Density = density === "compact" ? "comfortable" : "compact";
    setDensity(next);
    apply(next);
    localStorage.setItem(KEY, next);
  }
  return (
    <button className="btn-mini" onClick={toggle} title="Densità della vista" style={{ width: "100%" }}>
      {density === "compact" ? "Densità: compatta" : "Densità: comoda"}
    </button>
  );
}
