// Protezione di TUTTE le route della Console (Phase 1 S5).
// Nessuna sessione → /api/* = 401, pagine = redirect a /login.
// Esclusi: /api/auth (NextAuth), /login, asset statici. Next prefissa il matcher col basePath.
import { auth } from "@/lib/auth";

export default auth((req) => {
  if (req.auth) return; // sessione valida → passa
  const { pathname } = req.nextUrl;

  if (pathname.startsWith("/api/")) {
    return Response.json({ ok: false, message: "unauthorized" }, { status: 401 });
  }
  // clone() preserva il basePath (/console dietro nginx): redirect a /console/login, non /login.
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  url.searchParams.set("callbackUrl", pathname);
  return Response.redirect(url);
});

export const config = {
  matcher: ["/((?!api/auth|login|_next/static|_next/image|favicon.ico|.*\\.css$).*)"],
};
