// Tipi + client helpers per la scheda lead ricca (Brief 4). operator_uid sempre dalla sessione.
import { BP } from "@/lib/basePath";

export type LeadStage = { id: number; name: string; sequence: number; isWon: boolean; isLost: boolean };

export type LeadPartner = {
  id: number; name: string; email: string; phone: string;
  city: string; country: string; isCompany: boolean; role: string;
};

export type LeadDetail = {
  id: number;
  name: string;
  stageId: number;
  stageName: string;
  stages: LeadStage[];
  ownerUid: number;
  owner: string;
  expectedRevenue: number | null;
  probability: number | null;
  score: number | null;
  rottingState: string | null;
  createDate: string | null;
  daysOpen: number | null;
  nextAction: { date: string | null; summary: string } | null;
  partner: LeadPartner | false;
  company: { id: number; name: string } | false;
  dossier: { id: number; name: string; status: string; valueEstimate: number | null } | false;
  emailFrom: string;
  message?: string;
};

export type TimelineKind = "mail" | "campionatura" | "note";
export type LeadTimelineItem = {
  type: TimelineKind;
  date: string | null;
  title: string;
  subtitle: string;
  direction?: "inbound" | "outbound";
  shipmentId?: number;
};
export type LeadTimeline = { leadId: number; items: LeadTimelineItem[]; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getLead = (leadId: number) => post<LeadDetail>("/api/console/lead/get", { leadId });
export const getLeadTimeline = (leadId: number) => post<LeadTimeline>("/api/console/lead/timeline", { leadId });

export const rottingLabel: Record<string, { label: string; color: string }> = {
  fresh: { label: "Fresco", color: "#2F6B4F" },
  warning: { label: "In raffreddamento", color: "#C8A43A" },
  danger: { label: "A rischio", color: "#B23B3B" },
  dead: { label: "Morto", color: "#7A2E2E" },
};

export const timelineMeta: Record<TimelineKind, { label: string; color: string; icon: string }> = {
  mail: { label: "Mail", color: "#6B4A1E", icon: "✉" },
  campionatura: { label: "Campionatura", color: "#2F6B4F", icon: "📦" },
  note: { label: "Nota", color: "#8A8A8A", icon: "•" },
};
