"use client";
// Scena PRODUZIONE — operativo per officina/magazzino. MAI dati economici.
import { Scene, useToken } from "@/components/wallboard/Scene";
import {
  OrdiniDaEvadere,
  InProduzione,
  LavorazioniOggi,
  SpedizioniOggi,
  QcBloccanti,
} from "@/components/wallboard/tiles";

export default function ProduzioneScene() {
  const token = useToken();
  return (
    <Scene name="Produzione" columns={3}>
      <OrdiniDaEvadere token={token} />
      <InProduzione token={token} />
      <LavorazioniOggi token={token} />
      <SpedizioniOggi token={token} />
      <QcBloccanti token={token} />
    </Scene>
  );
}
