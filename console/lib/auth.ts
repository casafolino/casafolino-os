// NextAuth v5 (Auth.js) — auth per-umano della Console (Phase 1 S5).
// Sessione JWT firmata (AUTH_SECRET in console.prod.env), scadenza 12h. Porta SOLO
// operatorUid + name + allowed: NIENTE password, NIENTE sessione Odoo umana.
// I dati continuano via console_api (lib/odoo.ts): l'identità umana è solo attribution.
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { verifyOperator } from "@/lib/odooAuth";

export const { handlers, auth, signIn, signOut } = NextAuth({
  // Self-host dietro nginx: fidati dell'host inoltrato (Host/X-Forwarded-Proto).
  trustHost: true,
  // basePath = quello che VEDE l'handler: Next rimuove il basePath /console prima della
  // route, quindi Auth.js vede /api/auth/* (default). Il prefisso /console nei redirect
  // post-login è gestito esplicitamente nella server action (login/actions.ts).
  session: { strategy: "jwt", maxAge: 12 * 60 * 60 }, // 12h
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      name: "Odoo",
      credentials: {
        email: { label: "Email Odoo", type: "text" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (creds) => {
        const email = String(creds?.email ?? "");
        const password = String(creds?.password ?? "");
        const op = await verifyOperator(email, password);
        if (!op) return null; // credenziali errate OPPURE non in Console Operator
        // l'oggetto user finisce nel JWT (callback sotto): solo identità, mai segreti.
        return { id: String(op.uid), name: op.name, email: email.trim() };
      },
    }),
  ],
  callbacks: {
    jwt: ({ token, user }) => {
      if (user) {
        token.uid = Number(user.id);
        token.allowed = true;
      }
      return token;
    },
    session: ({ session, token }) => {
      session.operatorUid = typeof token.uid === "number" ? token.uid : undefined;
      session.allowed = Boolean(token.allowed);
      return session;
    },
  },
});
