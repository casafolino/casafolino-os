import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Console CasaFolino",
  description: "Console commerciale — relazione per partner, mail ovunque.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  );
}
