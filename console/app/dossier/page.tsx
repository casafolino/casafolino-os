// Dossier (read-only) — lente su res.partner: cerca un'azienda → apri il dossier
// (/partner/[id]: anagrafica + timeline mail/lead/ordini). Solo vista + navigazione.
import Link from "next/link";
import { getPartnerList } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest } from "@/components/Honest";

export const dynamic = "force-dynamic";

function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

export default async function DossierPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams;
  const partners = await getPartnerList(q);

  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
          <h2 style={{ fontSize: 19 }}>Dossier</h2>
          <span className="muted" style={{ fontSize: 12 }}>lente su res.partner · sola lettura</span>
        </div>

        {/* ricerca (GET, read-only) */}
        <form method="GET" className="row" style={{ gap: 8, marginBottom: 14 }}>
          <input name="q" defaultValue={q ?? ""} placeholder="Cerca azienda…" style={{
            flex: 1, maxWidth: 360, fontSize: 13, padding: "8px 11px",
            border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--paper)", color: "var(--ink)",
          }} />
          <button className="btn pri" type="submit">Cerca</button>
        </form>

        {partners.length === 0 ? (
          <EmptyHonest label={q ? `Nessuna azienda per "${q}".` : "Nessuna azienda."} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {partners.map((p) => (
              <Link key={p.id} href={`/partner/${p.id}`} className="card" style={{ padding: "11px 13px", display: "block" }}>
                <div className="row" style={{ gap: 10 }}>
                  <div style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--panel-2)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 12, flexShrink: 0 }}>{initials(p.name)}</div>
                  <div className="grow" style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: "var(--accent)" }} className="ell">{p.name} →</div>
                    <div className="muted ell" style={{ fontSize: 11 }}>{p.sub || "nessun dettaglio"}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
