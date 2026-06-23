import { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Editor from "./pages/Editor";

export type Client = {
  id: string;
  email: string;
  full_name: string;
  company: string;
  plan: string;
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

export default function App() {
  const [client, setClient] = useState<Client | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [editingSite, setEditingSite] = useState<Site | null>(null);

  if (!client) {
    return (
      <Login
        onLogin={(c, s) => {
          setClient(c);
          setSites(s);
        }}
      />
    );
  }

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
    <Dashboard
      client={client}
      sites={sites}
      onEditSite={setEditingSite}
      onLogout={() => {
        setClient(null);
        setSites([]);
      }}
    />
  );
}
