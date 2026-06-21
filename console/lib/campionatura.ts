// Tipi + client helpers per la campionatura. Le fetch usano BP (basePath /console).
// operator_uid NON è mai passato dal client: lo inietta il route server-side dalla sessione.
import { BP } from "@/lib/basePath";

export type TrafficLight = "green" | "yellow" | "red";
export type StepState = "da_fare" | "in_corso" | "confermato" | "saltato";
export type ShipmentState = "creato" | "preparazione" | "etichetta" | "spedito" | "consegnato";

export type ProductHit = { id: number; name: string; code: string; uom: string };

export type WizardLine = { productId: number; name: string; qty: number };

export type TimelineStep = {
  stepId: number;
  role: string;
  name: string;
  assignee: string;
  assigneeUid?: number;
  state: StepState;
  trafficLight: TrafficLight;
  hours: number;
  checkin?: string | null;
  checkout?: string | null;
};

export type Timeline = {
  shipmentId: number;
  name: string;
  partner: string;
  shipmentState: ShipmentState;
  carrier: string;
  tracking: string;
  orderId?: number;
  sampleCode: string;
  taskId?: number;
  taskState?: string;
  taskTrafficLight: TrafficLight;
  steps: TimelineStep[];
};

export type MyStep = {
  stepId: number;
  role: string;
  name: string;
  state: StepState;
  trafficLight: TrafficLight;
  hours: number;
  taskId: number;
  taskName: string;
  partner: string;
  isLogistica: boolean;
  canCheckin: boolean;
  shipmentId: number | false;
  carrier: string;
  tracking: string;
  shipmentState: string;
};

export type CreateResult = {
  ok?: boolean;
  order_id?: number;
  sample_code?: string;
  task_id?: number;
  shipment_id?: number;
  message?: string;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export type CampDefaults = {
  defaults: Record<string, { uid: number; name: string } | false>;
  operators: { uid: number; name: string }[];
};

export const getCampDefaults = () => post<CampDefaults>("/api/console/campionatura/defaults", {});

export const searchProducts = (query: string) =>
  post<ProductHit[]>("/api/console/campionatura/products", { query });

export const createCampionatura = (body: {
  partnerId?: number | null;
  leadId?: number | null;
  lines: { productId: number; qty: number }[];
  assignees?: Record<string, number>;
  carrier?: string;
}) => post<CreateResult>("/api/console/campionatura/create", body);

export const getTimeline = (shipmentId: number) =>
  post<Timeline>("/api/console/campionatura/timeline", { shipmentId });

export const listMySteps = () => post<MyStep[]>("/api/console/steps/list", {});

export const stepCheckin = (stepId: number) =>
  post<{ ok?: boolean; state?: string; message?: string }>("/api/console/steps/checkin", { stepId });

export const stepConfirm = (stepId: number, trackingCode?: string, carrier?: string) =>
  post<{ ok?: boolean; state?: string; message?: string }>("/api/console/steps/confirm", { stepId, trackingCode, carrier });

export const stepRemind = (stepId: number) =>
  post<{ ok?: boolean; message?: string }>("/api/console/steps/remind", { stepId });

// Etichette IT + colori semaforo (allineati al tema console).
export const roleLabel: Record<string, string> = {
  coordinazione: "Coordinazione",
  creazione: "Creazione",
  produzione: "Produzione",
  logistica: "Logistica",
  commerciale: "Commerciale",
  amministrazione: "Amministrazione",
  altro: "Altro",
};

export const stepStateLabel: Record<string, string> = {
  da_fare: "Da fare",
  in_corso: "In corso",
  confermato: "Confermato",
  saltato: "Saltato",
};

export const shipmentStateLabel: Record<string, string> = {
  creato: "Creato",
  preparazione: "In preparazione",
  etichetta: "Etichetta",
  spedito: "Spedito",
  consegnato: "Consegnato",
};

export const lightColor: Record<TrafficLight, string> = {
  green: "#2F6B4F",
  yellow: "#C8A43A",
  red: "#B23B3B",
};
