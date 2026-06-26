// Wrapper fetch condiviso con timeout duro (AbortController). Lezione console hang:
// l'esterno (VIES/Serper/Groq dietro i metodi gated) è best-effort, mai uno spinner infinito.
import { BP } from "@/lib/basePath";

export async function postJSON<T>(path: string, body: unknown, timeoutMs = 8000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${BP}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    return (await res.json()) as T;
  } catch (e) {
    if ((e as Error).name === "AbortError") {
      throw new Error("Il server non risponde (timeout). Riprova o procedi manualmente.");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}
