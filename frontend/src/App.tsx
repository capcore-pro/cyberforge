import { useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { BackendHealthProvider } from "@/context/BackendHealthContext";
import { AgentsStatusProvider } from "@/context/AgentsStatusContext";
import { GeneratorSessionProvider } from "@/context/GeneratorSessionContext";
import { PipelineActivityProvider } from "@/context/PipelineActivityContext";
import { ContactNotificationsProvider, useContactNotifications } from "@/context/ContactNotificationsContext";
import { getPublicDemoToken } from "@/lib/demo-route";
import type { AppPage } from "./lib/navigation";
import { ClientDemoPage } from "./pages/ClientDemoPage";
import { GeneratorPage } from "./pages/GeneratorPage";
import { HomePage } from "./pages/HomePage";
import { ClientsPage } from "./pages/ClientsPage";
import { PersoPage } from "./pages/PersoPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { VitrinesPage } from "./pages/VitrinesPage";
import { ApplicationWebPage } from "./pages/ApplicationWebPage";
import { SettingsPage } from "./pages/SettingsPage";

/**
 * Composant racine — navigation entre les pages principales.
 */
export default function App() {
  const demoToken = getPublicDemoToken();
  const [page, setPage] = useState<AppPage>("dashboard");

  if (demoToken) {
    return (
      <Layout>
        <ClientDemoPage token={demoToken} />
      </Layout>
    );
  }

  return (
    <ErrorBoundary>
      <BackendHealthProvider>
        <ContactNotificationsProvider>
          <AppWithNotifications page={page} setPage={setPage} />
        </ContactNotificationsProvider>
      </BackendHealthProvider>
    </ErrorBoundary>
  );
}

function AppWithNotifications({
  page,
  setPage,
}: {
  page: AppPage;
  setPage: (p: AppPage) => void;
}) {
  const { markAllSeen } = useContactNotifications();

  useEffect(() => {
    if (page === "clients") {
      void markAllSeen();
    }
  }, [page, markAllSeen]);

  function renderPage() {
    switch (page) {
      case "generator":
        return <GeneratorPage onOpenProjects={() => setPage("projects")} />;
      case "projects":
        return <ProjectsPage />;
      case "vitrines":
        return <VitrinesPage />;
      case "application_web":
        return <ApplicationWebPage />;
      case "clients":
        return <ClientsPage onOpenGenerator={() => setPage("generator")} />;
      case "perso":
        return <PersoPage onOpenGenerator={() => setPage("generator")} />;
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
    <AgentsStatusProvider>
      <GeneratorSessionProvider>
        <PipelineActivityProvider>
          <Layout>
            <AppShell currentPage={page} onNavigate={setPage}>
              {renderPage()}
            </AppShell>
          </Layout>
        </PipelineActivityProvider>
      </GeneratorSessionProvider>
    </AgentsStatusProvider>
  );
}
