// Pipeline kanban (Brief 6): board draggabile manager-only. Drag tra fasi → console_set_lead_stage;
// menu card → terminali Vinta/Persa/Standby. Card → /lead/[id]; lancio campionatura conservato.
// Barra ricerca universale in cima.
import { Sidebar } from "@/components/Sidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { SearchBar } from "@/components/SearchBar";

export const dynamic = "force-dynamic";

export default function Pipeline() {
  return (
    <div className="app">
      <Sidebar active="pipeline" variant="rail" />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Pipeline</h2>
          <SearchBar />
        </div>
        <KanbanBoard />
      </main>
    </div>
  );
}
