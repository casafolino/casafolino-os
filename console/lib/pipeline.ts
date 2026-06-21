// Brief 6 — tipi + helper client per kanban + ricerca universale. operator_uid dalla sessione.
import { BP } from "@/lib/basePath";

export type BoardCard = {
  id: number;
  name: string;
  partnerId: number | null;
  company: string;
  value: number | null;
  owner: string;
  score: number | null;
  rottingState: string | null;
  daysInStage: number | null;
};

export type BoardColumn = {
  stageId: number;
  name: string;
  sequence: number;
  count: number;
  cards: BoardCard[];
};

export type TerminalStage = { stageId: number; name: string; isWon: boolean };
export type Board = { columns: BoardColumn[]; terminalStages: TerminalStage[]; message?: string };

export type SearchItem = { id: number; title: string; subtitle: string };
export type SearchGroup = { type: "lead" | "partner" | "mail" | "dossier"; label: string; items: SearchItem[] };
export type SearchResult = { query: string; groups: SearchGroup[]; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getBoard = () => post<Board>("/api/console/pipeline/board", {});
export const setLeadStage = (leadId: number, stageId: number) =>
  post<{ ok?: boolean; stageId?: number; stageName?: string; terminal?: boolean; message?: string }>(
    "/api/console/pipeline/set-stage", { leadId, stageId });
export const universalSearch = (query: string) => post<SearchResult>("/api/console/search", { query });

// link per tipo risultato → dettaglio
export const searchHref: Record<SearchGroup["type"], (id: number) => string> = {
  lead: (id) => `/lead/${id}`,
  partner: (id) => `/partner/${id}`,
  mail: (id) => `/mail/${id}`,
  dossier: () => `/dossier`,
};

export const rottingColor: Record<string, string> = {
  fresh: "#2F6B4F", warning: "#C8A43A", danger: "#B23B3B", dead: "#7A2E2E",
};
