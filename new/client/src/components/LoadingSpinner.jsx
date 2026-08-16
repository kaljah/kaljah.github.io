import React from "react";
import "./LoadingSpinner.css";

import animationVideo from "../assets/loading_animation.mp4";

const LoadingSpinner = ({
  size = "medium",
  fullScreen = false,
  message = "Loading System Resources...",
  speed = 2.0, // Added speed prop
}) => {
  const sizeClass = `spinner-${size}`;
  const videoRef = React.useRef(null);

  React.useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  }, [speed]);

  const LoaderContent = () => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
      <div className={`stylish-theme-spinner ${sizeClass}`}>
        <div className="spinner-ring"></div>
        <div className="spinner-core"></div>
      </div>
      {message && <div className="loading-message-text">{message}</div>}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="loading-fullscreen">
        <LoaderContent />
      </div>
    );
  }

  return (
    <div className="loading-inline">
      <LoaderContent />
    </div>
  );
};

export default LoadingSpinner;
