// Sidebar riusabile — fedele a console_reference_v4.
// variant "full": Regia (184px, label + count). variant "rail": Inbox/Pipeline (54px, sole icone).
import Link from "next/link";
import { Icon } from "./Icons";

const NAV: { key: string; label: string; href: string; icon: string; count?: number }[] = [
  { key: "regia", label: "Regia", href: "/", icon: "home" },
  { key: "inbox", label: "Inbox", href: "/inbox", icon: "inbox", count: 7 },
  { key: "pipeline", label: "Pipeline", href: "/pipeline", icon: "kanban" },
  { key: "followup", label: "Follow-up", href: "/follow-up", icon: "clock" },
  { key: "fiere", label: "Fiere", href: "/fiere", icon: "fair" },
  { key: "dossier", label: "Dossier", href: "/dossier", icon: "folders" },
];

export function Sidebar({
  active,
  source,
  variant = "full",
}: {
  active: string;
  source?: string;
  variant?: "full" | "rail";
}) {
  if (variant === "rail") {
    return (
      <nav className="side rail">
        {NAV.map((n) => (
          <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""} title={n.label}>
            <Icon name={n.icon} color={n.key === active ? "var(--accent)" : "var(--faint)"} size={20} />
          </Link>
        ))}
        <span className="av" style={{ marginTop: "auto" }}>AF</span>
      </nav>
    );
  }
  return (
    <nav className="side">
      <div className="brand">CasaFolino</div>
      {NAV.map((n) => (
        <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""}>
          <Icon name={n.icon} />
          {n.label}
          {n.count ? <span className="cnt">{n.count}</span> : null}
        </Link>
      ))}
      <div className="me" style={{ marginTop: "auto" }}>
        <span className="av">AF</span>
        <span>Antonio</span>
      </div>
      <div className="src">dati: {source ?? "Odoo · folinofood"}</div>
    </nav>
  );
}
