"use client";
// Guscio di una scena wallboard: header CASAFOLINO + nome scena + freschezza + orologio,
// griglia bento, ticker opzionale. Supporta rotazione di sotto-viste (?rotate=N).
import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { FreshnessProvider, FreshnessBadge, useAlertActive } from "@/components/wallboard/freshness";

function Clock() {
  const [now, setNow] = useState<string>("");
  useEffect(() => {
    const fmt = () => new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
    setNow(fmt());
    const id = setInterval(() => setNow(fmt()), 15_000);
    return () => clearInterval(id);
  }, []);
  return <span className="wb-clock">{now}</span>;
}

/** Hook: token-scena dalla querystring (?k=). */
export function useToken(): string {
  const sp = useSearchParams();
  return sp.get("k") ?? "";
}

export interface SceneView {
  label: string;
  /** indice della vista "critica" su cui bloccarsi in presenza di alert (default: questa). */
  node: ReactNode;
}

function Grid({ columns, children }: { columns: number; children: ReactNode }) {
  return (
    <div className="wb-grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
      {children}
    </div>
  );
}

/** Corpo che ruota tra sotto-viste; si ferma sulla vista 0 (critica) se c'è un alert. */
function RotatingBody({
  columns,
  views,
  rotateSec,
}: {
  columns: number;
  views: SceneView[];
  rotateSec: number;
}) {
  const [idx, setIdx] = useState(0);
  const alert = useAlertActive();
  useEffect(() => {
    if (alert) {
      setIdx(0); // vista critica = prima
      return;
    }
    if (rotateSec <= 0 || views.length < 2) return;
    const id = setInterval(() => setIdx((i) => (i + 1) % views.length), rotateSec * 1000);
    return () => clearInterval(id);
  }, [alert, rotateSec, views.length]);
  return (
    <>
      <Grid columns={columns}>{views[idx]?.node}</Grid>
      {views.length > 1 && (
        <div className="wb-rot-dots">
          {views.map((v, i) => (
            <span key={i} className={`wb-rot-dot${i === idx ? " on" : ""}`} title={v.label} />
          ))}
        </div>
      )}
    </>
  );
}

export function Scene({
  name,
  columns,
  children,
  views,
  ticker,
}: {
  name: string;
  columns: number;
  children?: ReactNode;
  /** se fornito, abilita la rotazione (con ?rotate=N); altrimenti render statico. */
  views?: SceneView[];
  ticker?: ReactNode;
}) {
  const sp = useSearchParams();
  const rotateSec = parseInt(sp.get("rotate") ?? "0", 10) || 0;
  return (
    <FreshnessProvider>
      <main className="wb">
        <header className="wb-head">
          <span className="wb-brand">CASAFOLINO</span>
          <span className="wb-scene">
            {name}
            <FreshnessBadge />
          </span>
          <Clock />
        </header>
        {views && views.length && rotateSec > 0 ? (
          <RotatingBody columns={columns} views={views} rotateSec={rotateSec} />
        ) : (
          <Grid columns={columns}>{views ? views[0]?.node : children}</Grid>
        )}
        {ticker}
      </main>
    </FreshnessProvider>
  );
}
