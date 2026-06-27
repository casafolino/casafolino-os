// Dossier — raccolta CURATA dei soli clienti pinnati (is_dossier), per cartella.
// Non più lente su tutta l'anagrafica. Click su una card → fascicolo-cliente esistente (/partner/[id]).
import { Sidebar } from "@/components/Sidebar";
import { DossierBoard } from "@/components/DossierBoard";

export const dynamic = "force-dynamic";

export default function DossierPage() {
  return (
    <div className="app">
      <Sidebar active="dossier" variant="rail" />
      <main className="main">
        <DossierBoard />
      </main>
    </div>
  );
}
