// Mail (read-only) — 2 caselle (Antonio + Martina), filtrabile per casella.
// Solo vista + navigazione: nessun bottone azione (reply/convert/archive).
import Link from "next/link";
import { getMailAccounts, getMailList } from "@/lib/bundle";
import { Sidebar } from "@/components/Sidebar";
import { EmptyHonest, dateLabel } from "@/components/Honest";
import { operatorColor } from "@/lib/theme";

export const dynamic = "force-dynamic";

export default async function MailPage({ searchParams }: { searchParams: Promise<{ account?: string }> }) {
  const { account } = await searchParams;
  const accId = account && account !== "all" ? Number(account) : undefined;
  const [accounts, list] = await Promise.all([getMailAccounts(), getMailList(accId)]);

  const tabs = [{ id: "all", label: "Tutte", op: "other" as const }, ...accounts.map((a) => ({ id: String(a.id), label: a.name, op: a.operator }))];
  const current = account ?? "all";

  return (
    <div className="app">
      <Sidebar active="mail" variant="rail" />
      <main className="main">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
          <h2 style={{ fontSize: 19 }}>Mail</h2>
          <span className="muted" style={{ fontSize: 12 }}>{list.length} messaggi · sola lettura</span>
        </div>

        {/* filtro casella */}
        <div className="row" style={{ gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          {tabs.map((t) => {
            const on = current === t.id;
            return (
              <Link key={t.id} href={`/mail?account=${t.id}`} className="chip" style={{
                background: on ? "var(--ink)" : "var(--paper)", color: on ? "#fff" : "var(--ink)",
                border: "1px solid var(--line-2)", padding: "5px 11px",
              }}>
                {t.id !== "all" ? <span className="opdot" style={{ background: operatorColor[t.op] }} /> : null}
                {t.label}
              </Link>
            );
          })}
        </div>

        {list.length === 0 ? (
          <EmptyHonest label="Nessuna mail in questa casella." />
        ) : (
          <div className="card" style={{ overflow: "hidden" }}>
            {/* header */}
            <div className="row" style={{ padding: "8px 13px", borderBottom: "1px solid var(--line)", fontSize: 11, color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em" }}>
              <span style={{ width: 88, flexShrink: 0 }}>Data</span>
              <span style={{ width: 180, flexShrink: 0 }}>Mittente</span>
              <span className="grow">Oggetto</span>
              <span style={{ width: 200, flexShrink: 0 }}>Partner</span>
              <span style={{ width: 110, flexShrink: 0 }}>Stato link</span>
            </div>
            {list.map((m) => (
              <Link key={m.id} href={`/mail/${m.id}`} className="row" style={{
                padding: "9px 13px", borderBottom: "1px solid var(--line)", fontSize: 13, gap: 10,
              }}>
                <span className="muted" style={{ width: 88, flexShrink: 0, fontSize: 12 }}>{dateLabel(m.date)}</span>
                <span className="row" style={{ width: 180, flexShrink: 0, gap: 6 }}>
                  <span className="opdot" style={{ background: operatorColor[m.operator] }} />
                  <span className="ell" style={{ fontWeight: m.isRead ? 400 : 600 }}>{m.senderName}</span>
                </span>
                <span className="ell grow" style={{ fontWeight: m.isRead ? 400 : 600 }}>{m.subject}</span>
                <span className="ell" style={{ width: 200, flexShrink: 0 }}>
                  {m.linked ? <span style={{ color: "var(--accent)" }}>{m.partnerName}</span> : <span className="muted">mittente solo</span>}
                </span>
                <span style={{ width: 110, flexShrink: 0 }}>
                  {m.linked
                    ? <span className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)" }}>collegato</span>
                    : <span className="chip" style={{ background: "var(--panel-2)", color: "var(--muted)" }}>non collegato</span>}
                </span>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
