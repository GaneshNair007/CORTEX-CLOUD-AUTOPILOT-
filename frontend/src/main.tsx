import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./control-plane/Application";
import "./control-plane/theme.css";
import "./control-plane/brilean.css";
import "./control-plane/brilean-motion.css";

document.documentElement.dataset.brickAppearance = "light";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
