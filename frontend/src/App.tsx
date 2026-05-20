import { useState } from "react";
import { AppShell } from "./components/AppShell";
import { Layout } from "./components/Layout";
import type { AppPage } from "./lib/navigation";
import { GeneratorPage } from "./pages/GeneratorPage";
import { HomePage } from "./pages/HomePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";

/**
 * Composant racine — navigation entre les pages principales.
 */
export default function App() {
  const [page, setPage] = useState<AppPage>("dashboard");

  function renderPage() {
    switch (page) {
      case "generator":
        return <GeneratorPage onOpenProjects={() => setPage("projects")} />;
      case "projects":
        return <ProjectsPage />;
      case "settings":
        return <SettingsPage />;
      default:
        return (
          <HomePage
            onOpenGenerator={() => setPage("generator")}
            onOpenProjects={() => setPage("projects")}
          />
        );
    }
  }

  return (
    <Layout>
      <AppShell currentPage={page} onNavigate={setPage}>
        {renderPage()}
      </AppShell>
    </Layout>
  );
}
