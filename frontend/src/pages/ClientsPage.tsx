import { FichesModePage } from "@/components/FichesModePage";

interface ClientsPageProps {
  onOpenGenerator?: () => void;
}

/** Fiches clients commerciaux (est_perso = false). */
export function ClientsPage({ onOpenGenerator }: ClientsPageProps) {
  return <FichesModePage kind="client" onOpenGenerator={onOpenGenerator} />;
}
