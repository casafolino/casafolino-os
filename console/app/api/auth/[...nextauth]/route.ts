// NextAuth route handlers (signin/signout/session/csrf). Esclusa dalla protezione middleware.
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
