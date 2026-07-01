// Regia — dashboard unica, porta d'ingresso (Brief Regia+Dossier). Home della console.
// Ricerca cliente full-width → Dossier · 4 azioni rapide · 4 KPI · lista pipeline ordinata semaforo.
import { getRegia, getOperatorAccounts, getLibrary, getTemplates } from "@/lib/bundle";
import { auth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { SearchBar } from "@/components/SearchBar";
import { QuickTaskBar } from "@/components/QuickTaskBar";
import { RegiaActions } from "@/components/RegiaActions";
import { RegiaKpiRow, RegiaPipelineList } from "@/components/RegiaClient";

export const dynamic = "force-dynamic";

export default async function Regia() {
  const session = await auth();
  const [r, accounts, library, templates] = await Promise.all([
    getRegia(),
    getOperatorAccounts({ operatorUid: session?.operatorUid }),
    getLibrary(),
    getTemplates(),
  ]);

  return (
    <div className="app">
      <Sidebar active="regia" source={r.source === "mock" ? "mock" : "Odoo · folinofood"} />
      <main className="main">
        {/* Ricerca cliente full-width — atterra diretto sul Dossier (SearchBar → /partner/[id]) */}
        <div style={{ marginBottom: 14 }}>
          <SearchBar wide />
        </div>

        <h2 style={{ fontSize: 19, margin: "2px 0 2px" }}>Regia</h2>
        <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
          {r.subtitle || "Sala controllo — cerca un cliente, agisci, tieni d'occhio la pipeline."}
        </div>

        {/* 4 azioni rapide sempre visibili (bottoni) */}
        <RegiaActions accounts={accounts} library={library} templates={templates} />
        <QuickTaskBar />

        {/* 4 KPI */}
        <RegiaKpiRow />

        {/* Lista pipeline ordinata: rossi → gialli (giorni) → verdi. Click riga → Dossier. */}
        <h3 className="sec-title">Pipeline</h3>
        <RegiaPipelineList />
      </main>
    </div>
  );
}
