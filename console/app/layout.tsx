import type { Metadata } from "next";
import "./globals.css";
import { IconSprite } from "@/components/Icons";
import { CommandPalette } from "@/components/CommandPalette";
import { DensityInit } from "@/components/DensityToggle";

export const metadata: Metadata = {
  title: "Console CasaFolino",
  description: "Console commerciale, relazione per partner, mail ovunque.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>
        <DensityInit />
        <IconSprite />
        {children}
        <CommandPalette />
      </body>
    </html>
  );
}
