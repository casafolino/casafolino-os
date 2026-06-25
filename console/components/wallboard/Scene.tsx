"use client";
// Guscio di una scena wallboard: header CASAFOLINO + nome scena + orologio,
// griglia bento, ticker opzionale. Le pagine passano il contenuto (tile).
import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";

function Clock() {
  const [now, setNow] = useState<string>("");
  useEffect(() => {
    const fmt = () =>
      new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
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

export function Scene({
  name,
  columns,
  children,
  ticker,
}: {
  name: string;
  columns: number;
  children: ReactNode;
  ticker?: ReactNode;
}) {
  return (
    <main className="wb">
      <header className="wb-head">
        <span className="wb-brand">CASAFOLINO</span>
        <span className="wb-scene">{name}</span>
        <Clock />
      </header>
      <div className="wb-grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {children}
      </div>
      {ticker}
    </main>
  );
}
