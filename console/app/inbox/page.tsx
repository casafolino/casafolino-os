// Inbox: viste Coda/Inbox + bucket (Altro) + RICERCA full-record scoped e filtro mittente/partner.
// Tutto server-side, scope per-operatore (operator_uid dalla sessione). Ricerca paginata.
import { auth } from "@/lib/auth";
import { getInbox, getInboxAll, getBucket, getQueueCount, getSenderCounts, getOperatorAccounts, getLibrary, getTemplates, searchInbox, getPartnerBundle } from "@/lib/bundle";
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

  const [data, queueCount, senderCounts] = await Promise.all([
    searching
      ? searchInbox(sc, { q, senderEmail: sender, partnerId })
      : v === "queue" ? getInbox(sc) : v === "all" ? getInboxAll(sc) : getBucket(v as "keep" | "discard" | "trash", sc),
    getQueueCount(sc),
    // conteggi VERI per mittente (read_group) — solo per le viste non-ricerca.
    searching ? Promise.resolve({}) : getSenderCounts(sc, v),
  ]);
  const [accounts, library, templates] = await Promise.all([getOperatorAccounts(sc), getLibrary(), getTemplates()]);

  // Brief B perf: pre-carica SOLO il bundle del primo selezionato (~82ms) invece di 12 (~1s, ~60 RPC).
  // Gli altri si caricano on-demand alla selezione (InboxClient → /api/console/partner-bundle).
  const firstPid = data.items.find((i) => i.partnerId != null)?.partnerId ?? null;
  const bundles: Record<number, PartnerBundle> = {};
  if (firstPid != null) { const b = await getPartnerBundle(firstPid); if (b) bundles[firstPid] = b; }

  return (
    <div className="app">
      <Sidebar active="inbox" variant="rail" />
      <InboxClient
        items={data.items} bundles={bundles} initialSelectedId={data.selectedId}
        view={v} scopeAll={scopeAll} queueCount={queueCount} senderCounts={senderCounts} accounts={accounts} library={library} templates={templates}
        search={{ q: q ?? "", sender: sender ?? "", partner: partnerId ?? null, active: searching }}
      />
    </div>
  );
}
