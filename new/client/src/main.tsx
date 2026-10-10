// Language first: module-level labels are translated when their modules load.
import "./i18n";
import { createRoot } from "react-dom/client";
import "./styles/index.css";
import App from "./App";
import { installLabelLinker } from "./utils/a11yLabels";

const rootElement = document.getElementById("root");
if (rootElement) {
  createRoot(rootElement).render(<App />);
}

installLabelLinker();
