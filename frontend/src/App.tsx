import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";

/**
 * Composant racine de l'application CyberForge.
 * Assemble la mise en page et la page active.
 */
export default function App() {
  return (
    <Layout>
      <HomePage />
    </Layout>
  );
}
