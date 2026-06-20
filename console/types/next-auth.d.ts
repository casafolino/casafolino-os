// Augment NextAuth con i campi attribution della Console (S5).
import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    /** uid Odoo dell'operatore umano loggato — usato SOLO per attribution (Phase 2). */
    operatorUid?: number;
    /** true se l'utente è in group_console_operator. */
    allowed?: boolean;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    uid?: number;
    allowed?: boolean;
  }
}
