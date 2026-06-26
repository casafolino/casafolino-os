"use client";
// Scena DIREZIONE — "dove devo guardare oggi, cosa è fuori controllo?".
// Vista per sole eccezioni; fatturato ammesso per la direzione.
import { Scene, useToken } from "@/components/wallboard/Scene";
import { PannelloEccezioni, FatturatoMese, CutoffTile } from "@/components/wallboard/tiles";

export default function DirezioneScene() {
  const token = useToken();
  return (
    <Scene name="Direzione" columns={3}>
      <PannelloEccezioni token={token} />
      <FatturatoMese token={token} withMoney />
      <CutoffTile token={token} />
    </Scene>
  );
}
