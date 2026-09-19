import React from "react";
import QADashboard from "./QADashboard";

/**
 * Diagnostics page is now unified with the QA/QC dashboard to deliver
 * an integrated enterprise data assurance, health diagnostics, and anomaly resolution experience.
 */
const Diagnostics = (props) => {
  return <QADashboard {...props} />;
};

export default Diagnostics;
