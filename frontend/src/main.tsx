import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/index.css";

// Point d'entrée React — montage dans la fenêtre Electron (renderer)
const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Élément #root introuvable dans index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
