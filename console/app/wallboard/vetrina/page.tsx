"use client";
// Scena VETRINA — buyer-facing, ingresso / sala riunioni. Reputazionale.
import { Scene, useToken } from "@/components/wallboard/Scene";
import {
  PaesiExport,
  Certificazioni,
  Crescita,
  ProssimaFiera,
  SpedizioniOggi,
  Ticker,
} from "@/components/wallboard/tiles";

export default function VetrinaScene() {
  const token = useToken();
  return (
    <Scene name="Vetrina" columns={3} ticker={<Ticker token={token} />}>
      <PaesiExport token={token} />
      <Certificazioni token={token} />
      <Crescita token={token} />
      <ProssimaFiera token={token} />
      <SpedizioniOggi token={token} />
    </Scene>
  );
}
