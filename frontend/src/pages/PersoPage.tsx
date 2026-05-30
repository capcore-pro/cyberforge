import { PersonalProjectsPage } from "@/pages/PersonalProjectsPage";

interface PersoPageProps {
  onOpenGenerator: (opts: {
    usage: import("@/lib/personal-projects-api").PersonalUsage;
    priceEur: number | null;
    commercialDescription: string;
    title: string;
  }) => void;
}

/** Projets personnels Mat — distincts des projets clients. */
export function PersoPage({ onOpenGenerator }: PersoPageProps) {
  return <PersonalProjectsPage onOpenGenerator={onOpenGenerator} />;
}
