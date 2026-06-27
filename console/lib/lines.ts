// Lente linee di prodotto — helper client. Tutto read-only, dati nativi (no duplicazione).
import { postJSON } from "@/lib/http";

export type PartnerLine = { category_id: number; name: string; n_campionature: number; n_preventivi: number; n_ordini: number; value: number; state: "attivo" | "esplorazione" | "chiuso" };
export type LineHistoryItem = { kind: "campionatura" | "preventivo" | "ordine"; kind_label: string; id: number; name: string; date: string; amount: number; state: string; sample_code: string; model: string };

export type LineCatalogItem = { category_id: number; name: string };

export const getPartnerLines = (partner_id: number) =>
  postJSON<{ ok: boolean; partner_id: number; lines: PartnerLine[]; catalog: LineCatalogItem[] }>("/api/console/partner-lines", { partner_id });

export const getLineHistory = (partner_id: number, category_id: number) =>
  postJSON<{ ok: boolean; count: number; partner_name: string; category_name: string; items: LineHistoryItem[] }>("/api/console/line-history", { partner_id, category_id });
