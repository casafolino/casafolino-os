"use server";
// Sign-in via server action: la signIn server-side gestisce basePath/redirect senza
// dipendere dall'URL del client (robusto sotto /console dietro nginx).
import { redirect } from "next/navigation";
import { signIn } from "@/lib/auth";
import { AuthError } from "next-auth";

export async function authenticate(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  // callbackUrl arriva già STRIPPED dal middleware (es. "/", "/inbox"). Solo path interni.
  let callbackUrl = String(formData.get("callbackUrl") || "/");
  if (!callbackUrl.startsWith("/") || callbackUrl.startsWith("//")) callbackUrl = "/";
  try {
    // redirect:false → signIn imposta solo il cookie di sessione (nessun redirect interno
    // che ignorerebbe il basePath /console). On failure lancia AuthError.
    await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirect: false,
    });
  } catch (e) {
    if (e instanceof AuthError) {
      return "Accesso negato: credenziali errate o utente non abilitato alla Console.";
    }
    throw e;
  }
  // redirect() di Next aggiunge GIÀ il basePath /console → NON prefissarlo a mano (causava
  // /console/console → 404). Path interno: redirect("/") → Next → /console/.
  // Fuori dal try: lancia NEXT_REDIRECT, non va scambiato per errore di login.
  redirect(callbackUrl);
}
