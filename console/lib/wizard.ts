// Fase 1 — Wizard "da chiamata a preventivo": vat lookup (dedup+VIES), enrich 007, quotazione bozza.
import { postJSON } from "@/lib/http";

export type VatExisting = { id: number; name: string; vat: string; city: string; country: string; email: string; isCompany: boolean };
export type VatPrefill = { name: string; vat: string; street: string; city: string; zip: string; country: string };
export type ViesResult = { valid: boolean; name: string; street: string; city: string; zip: string; raw?: string } | null;

export type VatLookup = {
  ok?: boolean;
  normalizedVat: string;
  formatValid: boolean;
  isNew: boolean;
  existing: VatExisting[];
  vies: ViesResult;
  prefill: VatPrefill | null;
  message?: string;
};

export type Enrich007 = {
  ok?: boolean;
  enrichment: { sito: string; settore: string; dimensione: string; citta: string; paese: string };
  usedWeb: boolean;
  message?: string;
};

export type QuotationResult = {
  ok?: boolean;
  orderId?: number;
  name?: string;
  state?: string;
  amountTotal?: number;
  message?: string;
};

function post<T>(path: string, body: unknown): Promise<T> {
  return postJSON<T>(path, body);
}

export const vatLookup = (body: { vat?: string; name?: string }) =>
  post<VatLookup>("/api/console/wizard/vat-lookup", body);

export const enrich007 = (body: { name: string; vat?: string }) =>
  post<Enrich007>("/api/console/wizard/enrich-007", body);

export const createQuotation = (body: { partnerId: number; leadId?: number; lines: { productId: number; qty: number }[] }) =>
  post<QuotationResult>("/api/console/wizard/quotation", body);
