// Inbox 3-pane (schermo 2). Server: carica inbox/cestino + bundle dei partner risolti.
// ?view=trash → Cestino (stato trash). Client gestisce selezione + triage bulk.
import { getInbox, getTrash, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { InboxClient } from "@/components/InboxClient";
import type { PartnerBundle } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Inbox({ searchParams }: { searchParams: Promise<{ view?: string }> }) {
  const { view } = await searchParams;
  const isTrash = view === "trash";
  const data = isTrash ? await getTrash() : await getInbox();
  // Prefetch bundle SOLO per i primi N partner (pannello dettaglio). La lista resta a 200
  // per il triage bulk; evita il fan-out di centinaia di RPC che satura Odoo (timeout).
  const ids = [...new Set(data.items.map((i) => i.partnerId).filter((x): x is number => x != null))].slice(0, 12);
  const bundles: Record<number, PartnerBundle> = {};
  await Promise.all(ids.map(async (id) => { const b = await getPartnerBundle(id); if (b) bundles[id] = b; }));

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient items={data.items} bundles={bundles} initialSelectedId={data.selectedId} view={isTrash ? "trash" : "inbox"} />
    </div>
  );
}
