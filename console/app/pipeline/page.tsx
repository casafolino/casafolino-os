// Pipeline kanban (Brief 6): board draggabile manager-only. Drag tra fasi → console_set_lead_stage;
// menu card → terminali Vinta/Persa/Standby. Card → /lead/[id]; lancio campionatura conservato.
// Barra ricerca universale in cima.
import { Sidebar } from "@/components/Sidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { SearchBar } from "@/components/SearchBar";
import { QuickCreateLead, QuickCreateDossier } from "@/components/QuickCreate";
import { auth } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function Pipeline() {
  const session = await auth();
  const me = session?.user?.name ?? "";
  return (
    <div className="app">
      <Sidebar active="pipeline" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Pipeline</h2>
            <QuickCreateLead label="+ Lead" />
            <QuickCreateDossier label="+ Dossier" />
          </div>
          <SearchBar />
        </div>
        <KanbanBoard me={me} />
      </main>
    </div>
  );
}
