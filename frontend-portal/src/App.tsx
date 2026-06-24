import { useState, type Dispatch, type SetStateAction } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Editor from "./pages/Editor";
import Pricing from "./pages/Pricing";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Welcome from "./pages/Welcome";
import SubscriptionBanner from "./components/SubscriptionBanner";
import SubscriptionSuccess from "./pages/SubscriptionSuccess";

export type Client = {
  id: string;
  email: string;
  full_name: string;
  company: string;
  plan: string;
  subscription_status?: string;
  trial_ends_at?: string | null;
  subscription_ends_at?: string | null;
  billing_interval?: string;
  onboarding_done?: boolean;
  site_url?: string;
};

export type Site = {
  id: string;
  site_name: string;
  site_url: string;
  html_content: string;
  sector: string;
  project_type: string;
  last_deployed_at: string;
};

function AuthenticatedApp({
  client,
  sites,
  setSites,
  onLogout,
}: {
  client: Client;
  sites: Site[];
  setSites: Dispatch<SetStateAction<Site[]>>;
  onLogout: () => void;
}) {
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const clientId = localStorage.getItem("portal_client_id") || client.id;
  const needsOnboarding = client.onboarding_done === false;

  if (editingSite) {
    return (
      <Editor
        client={client}
        site={editingSite}
        onBack={() => setEditingSite(null)}
        onSaved={(updatedSite) => {
          setSites((prev) =>
            prev.map((s) => (s.id === updatedSite.id ? updatedSite : s)),
          );
          setEditingSite(null);
        }}
      />
    );
  }

  return (
    <>
      <SubscriptionBanner clientId={clientId} />
      <Routes>
        <Route
          path="/"
          element={
            <Navigate
              to={needsOnboarding ? "/welcome" : "/dashboard"}
              replace
            />
          }
        />
        <Route
          path="/dashboard"
          element={
            needsOnboarding ? (
              <Navigate to="/welcome" replace />
            ) : (
              <Dashboard
                client={client}
                sites={sites}
                onEditSite={setEditingSite}
                onLogout={onLogout}
              />
            )
          }
        />
        <Route
          path="*"
          element={
            <Navigate
              to={needsOnboarding ? "/welcome" : "/dashboard"}
              replace
            />
          }
        />
      </Routes>
    </>
  );
}

function AppShell() {
  const [client, setClient] = useState<Client | null>(null);
  const [sites, setSites] = useState<Site[]>([]);

  const clientId =
    client?.id || localStorage.getItem("portal_client_id") || "";
  const clientName = client?.full_name || client?.email || "";
  const siteUrl =
    client?.site_url || sites.find((s) => s.site_url)?.site_url || "";

  function handleLogin(c: Client, s: Site[]) {
    localStorage.setItem("portal_client_id", c.id);
    setClient(c);
    setSites(s);
  }

  function handleLogout() {
    localStorage.removeItem("portal_client_id");
    setClient(null);
    setSites([]);
  }

  function handleOnboardingComplete() {
    setClient((c) => (c ? { ...c, onboarding_done: true } : c));
  }

  const postLoginPath =
    client?.onboarding_done === false ? "/welcome" : "/dashboard";

  return (
    <Routes>
      <Route
        path="/login"
        element={
          client ? (
            <Navigate to={postLoginPath} replace />
          ) : (
            <Login onLogin={handleLogin} />
          )
        }
      />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/welcome"
        element={
          client ? (
            client.onboarding_done === false ? (
              <Welcome
                clientId={clientId}
                clientName={clientName}
                siteUrl={siteUrl}
                onComplete={handleOnboardingComplete}
              />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/subscription/success" element={<SubscriptionSuccess />} />
      <Route
        path="/*"
        element={
          client ? (
            <AuthenticatedApp
              client={client}
              sites={sites}
              setSites={setSites}
              onLogout={handleLogout}
            />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
