"use client";
// Scena LOGISTICA — "cosa deve partire oggi e ce la faccio?". Mai dati economici.
import { Scene, useToken } from "@/components/wallboard/Scene";
import {
  CutoffTile,
  DailyGoalTile,
  ProntiVsImballare,
  InRitardo,
  SpedizioniPartite,
} from "@/components/wallboard/tiles";

export default function LogisticaScene() {
  const token = useToken();
  return (
    <Scene name="Logistica" columns={3}>
      <CutoffTile token={token} />
      <DailyGoalTile token={token} dept="logistica" />
      <ProntiVsImballare token={token} />
      <InRitardo token={token} />
      <SpedizioniPartite token={token} />
    </Scene>
  );
}
