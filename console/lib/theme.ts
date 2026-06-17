// Palette CasaFolino + colori operatori (confermati da casafolino_crm_export).
import type { OperatorKey } from "./types";

export const palette = {
  cream: "#F5E6C8",
  brown: "#6B4A1E",
  gold: "#C8A43A",
  ink: "#2A2118",
  paper: "#FFFDF7",
  line: "rgba(107,74,30,0.18)",
} as const;

// Login → operatore. Allineato a USER_COLOR_MAP del modulo Odoo.
const OPERATOR_BY_LOGIN: Record<string, OperatorKey> = {
  "antonio@casafolino.com": "antonio",
  "josefina.lazzaro@casafolino.com": "josefina",
  "martina.sinopoli@casafolino.com": "martina",
};

export const operatorColor: Record<OperatorKey, string> = {
  antonio: "#3F8A4F", // verde
  josefina: "#8B5CF6", // prugna
  martina: "#6B4A1E", // marrone
  other: "#D1D5DB", // grigio neutro
};

// Tint (sfondo tenue) per chip score, fedele al riferimento.
export const operatorTint: Record<OperatorKey, string> = {
  antonio: "var(--op-antonio-t)",
  josefina: "var(--op-josefina-t)",
  martina: "var(--op-martina-t)",
  other: "var(--panel-2)",
};

export const operatorLabel: Record<OperatorKey, string> = {
  antonio: "Antonio",
  josefina: "Josefina",
  martina: "Martina",
  other: "Non assegnato",
};

export function operatorFromLogin(login: string | null | undefined): OperatorKey {
  if (!login) return "other";
  return OPERATOR_BY_LOGIN[login.trim().toLowerCase()] ?? "other";
}
