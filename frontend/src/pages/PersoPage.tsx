import { FichesModePage } from "@/components/FichesModePage";

interface PersoPageProps {
  onOpenGenerator?: () => void;
}

/** Projets personnels de Mat (est_perso = true). */
export function PersoPage({ onOpenGenerator }: PersoPageProps) {
  return <FichesModePage kind="perso" onOpenGenerator={onOpenGenerator} />;
}
