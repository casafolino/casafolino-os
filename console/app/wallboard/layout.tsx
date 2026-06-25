// Layout wallboard: carica i token CHIARI (wallboard.css) e i font display.
// I font sono caricati via <link> runtime (no build-time fetch): se offline, il
// browser ripiega sullo stack di sistema (Georgia/serif, system sans). Nessun
// import CSS esterno negli asset Odoo — questa è l'app Next, separata.
import type { Metadata } from "next";
import { Suspense } from "react";
import "./wallboard.css";

export const metadata: Metadata = {
  title: "Wallboard CasaFolino",
  description: "Monitor da reparto — produzione, vetrina, ufficio.",
};

export default function WallboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link
        href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap"
        rel="stylesheet"
      />
      <Suspense fallback={<main className="wb" />}>{children}</Suspense>
    </>
  );
}
