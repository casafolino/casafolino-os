// "Le mie lavorazioni" — pagina operatore (mobile-first). Gli step sono filtrati server-side
// per operatore della sessione (anti-spoof). Leggera: pensata per il telefono.
import { Sidebar } from "@/components/Sidebar";
import { LavorazioniClient } from "@/components/LavorazioniClient";

export const dynamic = "force-dynamic";

export default function LavorazioniPage() {
  return (
    <div className="app">
      <Sidebar active="lavorazioni" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "4px 0" }}>Le mie lavorazioni</h1>
        <LavorazioniClient />
      </main>
    </div>
  );
}
