import { useState } from "react";
import { AppShell } from "./components/AppShell";
import { Layout } from "./components/Layout";
import type { AppPage } from "./lib/navigation";
import { GeneratorPage } from "./pages/GeneratorPage";
import { HomePage } from "./pages/HomePage";

/**
 * Composant racine — navigation entre tableau de bord et générateur.
 */
export default function App() {
  const [page, setPage] = useState<AppPage>("dashboard");

  return (
    <Layout>
      <AppShell currentPage={page} onNavigate={setPage}>
        {page === "generator" ? (
          <GeneratorPage />
        ) : (
          <HomePage onOpenGenerator={() => setPage("generator")} />
        )}
      </AppShell>
    </Layout>
  );
}
