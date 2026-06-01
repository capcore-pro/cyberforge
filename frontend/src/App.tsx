import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { PageLoader } from "./components/PageLoader";
import { BackendHealthProvider } from "@/context/BackendHealthContext";
import { AgentsStatusProvider } from "@/context/AgentsStatusContext";
import { GeneratorSessionProvider } from "@/context/GeneratorSessionContext";
import { PipelineActivityProvider } from "@/context/PipelineActivityContext";
import { ContactNotificationsProvider, useContactNotifications } from "@/context/ContactNotificationsContext";
import { getPublicDemoToken } from "@/lib/demo-route";
import type { AppPage } from "./lib/navigation";
import { ClientDemoPage } from "./pages/ClientDemoPage";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const GeneratorPage = lazy(() =>
  import("./pages/GeneratorPage").then((m) => ({ default: m.GeneratorPage })),
);
const ProjectsPage = lazy(() =>
  import("./pages/ProjectsPage").then((m) => ({ default: m.ProjectsPage })),
);
const ClientsPage = lazy(() =>
  import("./pages/ClientsPage").then((m) => ({ default: m.ClientsPage })),
);
const PersoPage = lazy(() =>
  import("./pages/PersoPage").then((m) => ({ default: m.PersoPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);
const CockpitPage = lazy(() =>
  import("./pages/CockpitPage").then((m) => ({ default: m.CockpitPage })),
);
const MediaLibraryPage = lazy(() =>
  import("./pages/MediaLibraryPage").then((m) => ({ default: m.MediaLibraryPage })),
);
const AccountingPage = lazy(() =>
  import("./pages/AccountingPage").then((m) => ({ default: m.AccountingPage })),
);
const NewsletterPage = lazy(() =>
  import("./pages/NewsletterPage").then((m) => ({ default: m.NewsletterPage })),
);
const ToolboxPage = lazy(() =>
  import("./pages/ToolboxPage").then((m) => ({ default: m.ToolboxPage })),
);

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

/** Liens externes depuis les iframes d'aperçu HTML (postMessage). */
function usePreviewExternalLinkBridge(): void {
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const data = event.data as { type?: string; url?: string } | null;
      if (data?.type !== "cyberforge-open-external" || typeof data.url !== "string") {
        return;
      }
      const url = data.url.trim();
      if (!url) {
        return;
      }
      void window.cyberforge?.openExternal?.(url);
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);
}

function AppWithNotifications({
  page,
  setPage,
}: {
  page: AppPage;
  setPage: (p: AppPage) => void;
}) {
  usePreviewExternalLinkBridge();
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
      sessionStorage.setItem(
        "cyberforge.personalProjectDraft",
        JSON.stringify(opts),
      );
    },
    [setPage],
  );

  const openProjects = useCallback(() => {
    setGeneratorFromProjects(false);
    setGeneratorFromPerso(false);
    setPage("projects");
  }, [setPage]);

  const openPerso = useCallback(() => {
    setGeneratorFromProjects(false);
    setGeneratorFromPerso(false);
    setPage("perso");
  }, [setPage]);

  function renderPage() {
    switch (page) {
      case "generator":
        return (
          <GeneratorPage
            onOpenProjects={openProjects}
            onOpenPerso={openPerso}
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
              <Suspense fallback={<PageLoader />}>{renderPage()}</Suspense>
            </AppShell>
          </Layout>
        </PipelineActivityProvider>
      </GeneratorSessionProvider>
    </AgentsStatusProvider>
  );
}
