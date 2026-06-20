// Inbox: due viste primarie — Coda (to-do non-triate) e Inbox (record completo, tutti gli stati
// escl. cestino). Bucket Tenute/Scartate/Cestino nel menu Altro. Scope per-operatore server-side.
import { auth } from "@/lib/auth";
import { getInbox, getInboxAll, getBucket, getQueueCount, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { InboxClient, type InboxView } from "@/components/InboxClient";
import type { PartnerBundle } from "@/lib/types";

export const dynamic = "force-dynamic";

const VIEWS = new Set<InboxView>(["queue", "all", "keep", "discard", "trash"]);

export default async function Inbox({ searchParams }: { searchParams: Promise<{ view?: string; scope?: string }> }) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  const { view, scope } = await searchParams;
  const scopeAll = scope === "all";
  const sc = { operatorUid, scopeAll };

  const v: InboxView = VIEWS.has(view as InboxView) ? (view as InboxView) : "queue";
  const [data, queueCount] = await Promise.all([
    v === "queue" ? getInbox(sc) : v === "all" ? getInboxAll(sc) : getBucket(v as "keep" | "discard" | "trash", sc),
    getQueueCount(sc),
  ]);

  // Prefetch bundle solo per i primi N partner (evita fan-out RPC → timeout).
  const ids = [...new Set(data.items.map((i) => i.partnerId).filter((x): x is number => x != null))].slice(0, 12);
  const bundles: Record<number, PartnerBundle> = {};
  await Promise.all(ids.map(async (id) => { const b = await getPartnerBundle(id); if (b) bundles[id] = b; }));

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient items={data.items} bundles={bundles} initialSelectedId={data.selectedId} view={v} scopeAll={scopeAll} queueCount={queueCount} />
    </div>
  );
}
