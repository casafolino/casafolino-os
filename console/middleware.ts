// Protezione di TUTTE le route della Console (Phase 1 S5).
// Nessuna sessione → /api/* = 401, pagine = redirect a /login.
// Esclusi: /api/auth (NextAuth), /login, asset statici. Next prefissa il matcher col basePath.
import { auth } from "@/lib/auth";

// Brief 5 — superficie consentita all'OPERATORE (non-manager). Tutto il resto = manager-only.
// I path sono SENZA basePath (Next rimuove /console prima del middleware).
const OPERATOR_ALLOWED = ["/lavorazioni", "/api/console/steps", "/api/console/tasks"];
function isOperatorAllowed(pathname: string): boolean {
  return OPERATOR_ALLOWED.some((p) => pathname === p || pathname.startsWith(p + "/") || pathname.startsWith(p));
}

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // 1) Nessuna sessione → 401 (api) / redirect login (pagine).
  if (!req.auth) {
    if (pathname.startsWith("/api/")) {
      return Response.json({ ok: false, message: "unauthorized" }, { status: 401 });
    }
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("callbackUrl", pathname);
    return Response.redirect(url);
  }

  // 2) Sessione valida ma OPERATORE su superficie manager → nega (difesa in profondità,
  //    non solo UI). Manager → passa ovunque.
  const role = (req.auth as { role?: string }).role;
  if (role !== "manager" && !isOperatorAllowed(pathname)) {
    if (pathname.startsWith("/api/")) {
      return Response.json({ ok: false, message: "forbidden: operatore" }, { status: 403 });
    }
    const url = req.nextUrl.clone();
    url.pathname = "/lavorazioni";
    url.search = "";
    return Response.redirect(url);
  }
  return; // ok
});

export const config = {
  // "/" copre la root sotto basePath (bare /console): il catch-all richiede /console/<x>
  // e da solo lascerebbe passare /console senza sessione. Entrambi → root + sotto-path protetti.
  matcher: ["/", "/((?!api/auth|login|_next/static|_next/image|favicon.ico|.*\\.css$).*)"],
};
