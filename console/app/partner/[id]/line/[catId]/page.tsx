// WI-B — vista linea: /partner/[id]/line/[catId]. Lente sui nativi (sale.order per partner+categoria).
import { Sidebar } from "@/components/Sidebar";
import { LineView } from "@/components/LineView";

export const dynamic = "force-dynamic";

export default async function LinePage({ params }: { params: Promise<{ id: string; catId: string }> }) {
  const { id, catId } = await params;
  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main">
        <LineView partnerId={Number(id)} categoryId={Number(catId)} />
      </main>
    </div>
  );
}
