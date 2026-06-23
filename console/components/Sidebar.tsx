// Sidebar riusabile — fedele a console_reference_v4.
// variant "full": Regia (184px, label + count). variant "rail": Inbox/Pipeline (54px, sole icone).
// "Mail" demotata in un gruppo secondario "Altro" (overflow): raggiungibile, non in primo piano.
import Link from "next/link";
import { Icon } from "./Icons";
import { DensityToggle } from "./DensityToggle";

type NavItem = { key: string; label: string; href: string; icon: string; count?: number };

// Nav PRIMARIA (Mail rimossa).
const NAV: NavItem[] = [
  { key: "regia", label: "Regia", href: "/", icon: "home" },
  { key: "inbox", label: "Inbox", href: "/inbox", icon: "inbox", count: 7 },
  { key: "pipeline", label: "Pipeline", href: "/pipeline", icon: "kanban" },
  { key: "lavorazioni", label: "Lavorazioni", href: "/lavorazioni", icon: "check" },
  { key: "followup", label: "Follow-up", href: "/follow-up", icon: "clock" },
  { key: "fiere", label: "Fiere", href: "/fiere", icon: "fair" },
  { key: "dossier", label: "Dossier", href: "/dossier", icon: "folders" },
];

// Nav SECONDARIA / overflow "Altro": Mail demotata qui.
const NAV_SECONDARY: NavItem[] = [
  { key: "mail", label: "Mail", href: "/mail", icon: "mail" },
];

export function Sidebar({
  active,
  source,
  variant = "full",
  role = "manager",
}: {
  active: string;
  source?: string;
  variant?: "full" | "rail";
  role?: "manager" | "operator";
}) {
  // Brief 5 — operatore: vede SOLO Lavorazioni (le altre route gli sono negate dal middleware).
  const nav = role === "operator" ? NAV.filter((n) => n.key === "lavorazioni") : NAV;
  const navSecondary = role === "operator" ? [] : NAV_SECONDARY;
  if (variant === "rail") {
    return (
      <nav className="side rail">
        {nav.map((n) => (
          <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""} title={n.label}>
            <Icon name={n.icon} color={n.key === active ? "var(--accent)" : "var(--faint)"} size={20} />
          </Link>
        ))}
        {/* overflow "Altro" — separato, dimmato */}
        <div style={{ height: 1, background: "var(--line)", margin: "6px 8px", opacity: 0.6 }} />
        {navSecondary.map((n) => (
          <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""} title={`${n.label} (Altro)`} style={{ opacity: 0.55 }}>
            <Icon name={n.icon} color={n.key === active ? "var(--accent)" : "var(--faint)"} size={18} />
          </Link>
        ))}
        <span className="av" style={{ marginTop: "auto" }}>AF</span>
      </nav>
    );
  }
  return (
    <nav className="side">
      <div className="brand">CasaFolino</div>
      {nav.map((n) => (
        <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""}>
          <Icon name={n.icon} />
          {n.label}
          {n.count ? <span className="cnt">{n.count}</span> : null}
        </Link>
      ))}
      {/* sezione secondaria "Altro" */}
      <div style={{ margin: "10px 0 4px", padding: "0 12px", fontSize: 10, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--faint)" }}>Altro</div>
      {navSecondary.map((n) => (
        <Link key={n.key} href={n.href} className={n.key === active ? "on" : ""} style={{ opacity: 0.7 }}>
          <Icon name={n.icon} />
          {n.label}
        </Link>
      ))}
      <div style={{ marginTop: "auto", padding: "0 8px 6px" }}>
        <DensityToggle />
      </div>
      <div className="me">
        <span className="av">AF</span>
        <span>Antonio</span>
      </div>
      <div className="src">dati: {source ?? "Odoo · folinofood"}</div>
    </nav>
  );
}
