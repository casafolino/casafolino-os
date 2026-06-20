// Inbox: viste Coda/Inbox + bucket (Altro) + RICERCA full-record scoped e filtro mittente/partner.
// Tutto server-side, scope per-operatore (operator_uid dalla sessione). Ricerca paginata.
import { auth } from "@/lib/auth";
import { getInbox, getInboxAll, getBucket, getQueueCount, searchInbox, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { InboxClient, type InboxView } from "@/components/InboxClient";
import type { PartnerBundle } from "@/lib/types";

export const dynamic = "force-dynamic";

const VIEWS = new Set<InboxView>(["queue", "all", "keep", "discard", "trash"]);

export default async function Inbox({ searchParams }: {
  searchParams: Promise<{ view?: string; scope?: string; q?: string; sender?: string; partner?: string }>;
}) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  const { view, scope, q, sender, partner } = await searchParams;
  const scopeAll = scope === "all";
  const sc = { operatorUid, scopeAll };

  const v: InboxView = VIEWS.has(view as InboxView) ? (view as InboxView) : "queue";
  const partnerId = partner ? Number(partner) : undefined;
  const searching = Boolean((q && q.trim()) || sender || partnerId);

  const [data, queueCount] = await Promise.all([
    searching
      ? searchInbox(sc, { q, senderEmail: sender, partnerId })
      : v === "queue" ? getInbox(sc) : v === "all" ? getInboxAll(sc) : getBucket(v as "keep" | "discard" | "trash", sc),
    getQueueCount(sc),
  ]);

  const ids = [...new Set(data.items.map((i) => i.partnerId).filter((x): x is number => x != null))].slice(0, 12);
  const bundles: Record<number, PartnerBundle> = {};
  await Promise.all(ids.map(async (id) => { const b = await getPartnerBundle(id); if (b) bundles[id] = b; }));

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient
        items={data.items} bundles={bundles} initialSelectedId={data.selectedId}
        view={v} scopeAll={scopeAll} queueCount={queueCount}
        search={{ q: q ?? "", sender: sender ?? "", partner: partnerId ?? null, active: searching }}
      />
    </div>
  );
}
