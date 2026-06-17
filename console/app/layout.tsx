import type { Metadata } from "next";
import "./globals.css";
import { IconSprite } from "@/components/Icons";

export const metadata: Metadata = {
  title: "Console CasaFolino",
  description: "Console commerciale, relazione per partner, mail ovunque.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>
        <IconSprite />
        {children}
      </body>
    </html>
  );
}
