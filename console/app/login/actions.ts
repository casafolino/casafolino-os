"use server";
// Sign-in via server action: la signIn server-side gestisce basePath/redirect senza
// dipendere dall'URL del client (robusto sotto /console dietro nginx).
import { signIn } from "@/lib/auth";
import { AuthError } from "next-auth";

export async function authenticate(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  const callbackUrl = String(formData.get("callbackUrl") || "/");
  try {
    await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirectTo: callbackUrl,
    });
  } catch (e) {
    // AuthError = credenziali errate o utente non in allowlist → messaggio generico.
    if (e instanceof AuthError) {
      return "Accesso negato: credenziali errate o utente non abilitato alla Console.";
    }
    // NEXT_REDIRECT (login riuscito) e altri errori devono propagare.
    throw e;
  }
}
