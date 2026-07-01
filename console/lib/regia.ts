// Regia + Dossier unificati — tipi + helper client. operator_uid iniettato server-side.
import { postJSON } from "@/lib/http";

// ── KPI Regia ───────────────────────────────────────────────────────
export type RegiaKpis = {
  attivi: number;
  fermi3: number;
  scadenzaOggi: number;
  nuovi7: number;
  message?: string;
};

// ── Lista pipeline Regia (flat, ordinata semaforo) ──────────────────
export type RegiaPipelineRow = {
  leadId: number;
  partnerId: number | null;
  company: string;
  stage: string;
  owner: string;
  ownerInitials: string;
  activityState: string | null; // fresh | warning | danger | neutral
  daysInactive: number | null;
  value: number;
};
export type RegiaPipeline = {
  items: RegiaPipelineRow[];
  total: number;
  hasMore: boolean;
  message?: string;
};

// ── Dossier cliente ─────────────────────────────────────────────────
export type DossierMetrics = {
  ultimoOrdine: { name: string; amount: number; date: string | null } | null;
  fatturato12m: number;
  stage: string | null;
  taskAperti: number;
};
export type DossierHeader = {
  partner: {
    id: number;
    name: string;
    isCompany: boolean;
    email: string;
    city: string;
    country: string;
    owner: string;
    ownerInitials: string;
  };
  semaforo: string; // fresh | warning | danger | neutral
  semaforoDays: number | null;
  tags: string[];
  metrics: DossierMetrics;
  message?: string;
};

export type TimelineItem = {
  type: "order" | "mail" | "task" | "sample" | "note";
  icon: string;
  date: string; // ISO
  title: string;
  subtitle: string;
  author: string;
};
export type DossierTimeline = {
  items: TimelineItem[];
  total: number;
  hasMore: boolean;
  message?: string;
};

// colore semaforo (rotting reale): neutral = grigio (mai rosso falso)
export const semaforoColor: Record<string, string> = {
  fresh: "#2F6B4F",
  warning: "#C8A43A",
  danger: "#B23B3B",
  neutral: "#C4C6CB",
};

// colore per tipo evento timeline (allineato ai mockup: offerta=verde, mail=blu, ecc.)
export const timelineColor: Record<TimelineItem["type"], string> = {
  order: "#2F6B4F",
  mail: "#355F8B",
  task: "#B17B27",
  sample: "#C8A43A",
  note: "#6B4A66",
};

export const timelineIcon: Record<TimelineItem["type"], string> = {
  order: "🧾",
  mail: "✉",
  task: "✓",
  sample: "📦",
  note: "📝",
};

function post<T>(path: string, body: unknown): Promise<T> {
  return postJSON<T>(path, body);
}

export const getRegiaKpis = () => post<RegiaKpis>("/api/console/regia/kpis", {});
export const getRegiaPipeline = (limit = 100, offset = 0) =>
  post<RegiaPipeline>("/api/console/regia/pipeline", { limit, offset });
export const getPartnerDossier = (partnerId: number) =>
  post<DossierHeader>("/api/console/partner/dossier", { partnerId });
export const getPartnerTimeline = (partnerId: number, limit = 25, offset = 0) =>
  post<DossierTimeline>("/api/console/partner/timeline", { partnerId, limit, offset });

export function money(n: number | null | undefined): string {
  const v = Number(n || 0);
  return "€ " + v.toLocaleString("it-IT", { maximumFractionDigits: 0 });
}
