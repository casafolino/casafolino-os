// Dossier curati — helper client. Tutte le scritture via metodi gated+auditati (operator_uid dalla sessione).
import { postJSON } from "@/lib/http";

export type DossierCard = { id: number; name: string; email: string; city: string; country: string; is_company: boolean; folder_id: number | false };
export type DossierGroup = { id: number | false; name: string; color: number; partners: DossierCard[] };
export type DossierFolder = { id: number; name: string; color: number; count: number };

export const getDossierList = (query?: string) =>
  postJSON<{ ok: boolean; total: number; groups: DossierGroup[] }>("/api/console/dossier/list", { query: query ?? "" });

export const getFolders = () =>
  postJSON<{ ok: boolean; folders: DossierFolder[] }>("/api/console/dossier/folders", {});

export const toggleDossier = (b: { partner_id: number; is_dossier: boolean; folder_id?: number | null; new_folder_name?: string }) =>
  postJSON<{ ok: boolean; partner_id: number; is_dossier: boolean; folder_id: number | false; message?: string }>("/api/console/dossier/pin", b);

export const createFolder = (name: string) =>
  postJSON<{ ok: boolean; id: number; name: string; message?: string }>("/api/console/dossier/folder", { mode: "create", name });

export const renameFolder = (folder_id: number, name: string) =>
  postJSON<{ ok: boolean; id: number; name: string; message?: string }>("/api/console/dossier/folder", { mode: "rename", folder_id, name });
