import React from "react";
import "./LoadingSpinner.css";

const LoadingSpinner = ({
  size = "medium",
  fullScreen = false,
  message = "Loading System Resources...",
}) => {
  const sizeClass = `spinner-${size}`;

  // plain element, not a component defined during render (it would remount on every render)
  const content = (
    <div className="flex! flex-col! items-center! gap-[1.5rem]!">
      <div className={`stylish-theme-spinner ${sizeClass}`}>
        <div className="spinner-ring"></div>
        <div className="spinner-core"></div>
      </div>
      {message && <div className="loading-message-text">{message}</div>}
    </div>
  );

  return <div className={fullScreen ? "loading-fullscreen" : "loading-inline"}>{content}</div>;
};

export default LoadingSpinner;
