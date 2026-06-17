// Inbox 3-pane (schermo 2). Server: carica inbox + bundle dei partner risolti; client gestisce la selezione.
import { getInbox, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { InboxClient } from "@/components/InboxClient";
import type { PartnerBundle } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Inbox() {
  const inbox = await getInbox();
  const ids = [...new Set(inbox.items.map((i) => i.partnerId).filter((x): x is number => x != null))];
  const bundles: Record<number, PartnerBundle> = {};
  await Promise.all(ids.map(async (id) => { const b = await getPartnerBundle(id); if (b) bundles[id] = b; }));

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient items={inbox.items} bundles={bundles} initialSelectedId={inbox.selectedId} />
    </div>
  );
}
