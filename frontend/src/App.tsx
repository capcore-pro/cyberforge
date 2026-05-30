import { useCallback, useEffect, useMemo, useState } from "react";
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
import { DashboardPage } from "./pages/DashboardPage";
import { ClientsPage } from "./pages/ClientsPage";
import { PersoPage } from "./pages/PersoPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { CockpitPage } from "./pages/CockpitPage";
import { MediaLibraryPage } from "./pages/MediaLibraryPage";
import { AccountingPage } from "./pages/AccountingPage";
import { NewsletterPage } from "./pages/NewsletterPage";
import { ToolboxPage } from "./pages/ToolboxPage";

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
  const [generatorFromProjects, setGeneratorFromProjects] = useState(false);
  const [generatorFromPerso, setGeneratorFromPerso] = useState(false);

  useEffect(() => {
    if (page === "clients") {
      void markAllSeen();
    }
  }, [page, markAllSeen]);

  const openGeneratorFromProjects = useCallback(() => {
    setGeneratorFromProjects(true);
    setGeneratorFromPerso(false);
    setPage("generator");
  }, [setPage]);

  const openGeneratorFromPerso = useCallback(
    (opts: {
      usage: import("@/lib/personal-projects-api").PersonalUsage;
      priceEur: number | null;
      commercialDescription: string;
      title: string;
    }) => {
      setGeneratorFromPerso(true);
      setGeneratorFromProjects(false);
      setPage("generator");
      // Options applied via GeneratorPage effect reading sessionStorage bridge
      sessionStorage.setItem(
        "cyberforge.personalProjectDraft",
        JSON.stringify(opts),
      );
    },
    [setPage],
  );

  function renderPage() {
    switch (page) {
      case "generator":
        return (
          <GeneratorPage
            onOpenProjects={() => {
              setGeneratorFromProjects(false);
              setGeneratorFromPerso(false);
              setPage("projects");
            }}
            onOpenPerso={() => {
              setGeneratorFromProjects(false);
              setGeneratorFromPerso(false);
              setPage("perso");
            }}
            showBackToProjects={generatorFromProjects}
            showBackToPerso={generatorFromPerso}
            personalMode={generatorFromPerso}
          />
        );
      case "projects":
        return (
          <ProjectsPage
            onNavigate={setPage}
            onOpenGenerator={openGeneratorFromProjects}
          />
        );
      case "clients":
        return <ClientsPage onOpenGenerator={() => setPage("generator")} />;
      case "perso":
        return <PersoPage onOpenGenerator={openGeneratorFromPerso} />;
      case "settings":
        return <SettingsPage />;
      case "cockpit":
        return <CockpitPage />;
      case "media_library":
        return <MediaLibraryPage />;
      case "toolbox":
        return <ToolboxPage />;
      case "accounting":
        return <AccountingPage />;
      case "newsletter":
        return <NewsletterPage />;
      default:
        return <DashboardPage onNavigate={setPage} />;
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
