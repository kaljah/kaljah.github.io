import { createRoot } from "react-dom/client";
import "./styles/index.css";
import App from "./App.jsx";
import { installLabelLinker } from "./utils/a11yLabels";

createRoot(document.getElementById("root")).render(
  <App />
);

installLabelLinker();
