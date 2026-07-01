// Board Lavorazioni per-assegnatario + Pool — vista MANAGER. Non in OPERATOR_ALLOWED:
// il middleware reindirizza gli operatori a /lavorazioni; solo i manager la vedono.
import { Sidebar } from "@/components/Sidebar";
import { TaskBoard } from "@/components/TaskBoard";
import { auth } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function LavorazioniBoardPage() {
  const session = await auth();
  const role = session?.role === "manager" ? "manager" : "operator";
  return (
    <div className="app">
      <Sidebar active="lavorazioni" variant="rail" role={role} />
      <main className="main" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "4px 0" }}>Lavorazioni — Board</h1>
        <TaskBoard />
      </main>
    </div>
  );
}
