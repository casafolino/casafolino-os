// Inbox 3-pane (schermo 2). Coda di triage scoped all'operatore loggato (server-side).
// ?view=inbox|keep|discard|trash (bucket), ?scope=all (toggle "Tutte"). operator_uid dalla sessione.
import { auth } from "@/lib/auth";
import { getInbox, getBucket, getPartnerBundle } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { InboxClient, type InboxView } from "@/components/InboxClient";
import type { PartnerBundle } from "@/lib/types";

export const dynamic = "force-dynamic";

const BUCKETS = new Set(["keep", "discard", "trash"]);

export default async function Inbox({ searchParams }: { searchParams: Promise<{ view?: string; scope?: string }> }) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  const { view, scope } = await searchParams;
  const scopeAll = scope === "all";
  const sc = { operatorUid, scopeAll };

  const v: InboxView = (view && BUCKETS.has(view) ? view : "inbox") as InboxView;
  const data = v === "inbox" ? await getInbox(sc) : await getBucket(v as "keep" | "discard" | "trash", sc);

  // Prefetch bundle solo per i primi N partner (pannello dettaglio): evita fan-out RPC → timeout.
  const ids = [...new Set(data.items.map((i) => i.partnerId).filter((x): x is number => x != null))].slice(0, 12);
  const bundles: Record<number, PartnerBundle> = {};
  await Promise.all(ids.map(async (id) => { const b = await getPartnerBundle(id); if (b) bundles[id] = b; }));

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient items={data.items} bundles={bundles} initialSelectedId={data.selectedId} view={v} scopeAll={scopeAll} />
    </div>
  );
}
