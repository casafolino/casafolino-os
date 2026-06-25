"use client";
// Scena UFFICIO / COMMERCIALE — back office interno. Qui i KPI economici sono ammessi.
import { Scene, useToken } from "@/components/wallboard/Scene";
import {
  FatturatoMese,
  Pipeline,
  OrdiniDaEvadere,
  InProduzione,
  ProssimaFiera,
  Ticker,
} from "@/components/wallboard/tiles";

export default function UfficioScene() {
  const token = useToken();
  return (
    <Scene name="Ufficio" columns={3} ticker={<Ticker token={token} />}>
      <FatturatoMese token={token} withMoney />
      <Pipeline token={token} withMoney />
      <OrdiniDaEvadere token={token} withMoney />
      <InProduzione token={token} withMoney />
      <ProssimaFiera token={token} withMoney />
    </Scene>
  );
}
