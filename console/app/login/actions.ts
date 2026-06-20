"use server";
// Sign-in via server action: la signIn server-side gestisce basePath/redirect senza
// dipendere dall'URL del client (robusto sotto /console dietro nginx).
import { redirect } from "next/navigation";
import { signIn } from "@/lib/auth";
import { AuthError } from "next-auth";

const BP = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export async function authenticate(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  const callbackUrl = String(formData.get("callbackUrl") || "/");
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
  // Redirect esplicito col prefisso basePath (/console). redirect() lancia NEXT_REDIRECT
  // → fuori dal try così non viene scambiato per errore di login.
  redirect(`${BP}${callbackUrl}`);
}
