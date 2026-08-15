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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
      <div className={`modern-loader-container ${sizeClass}`}>
        <svg
          className="rotating-svg-loader"
          width={size === 'large' ? '120' : '64'}
          height={size === 'large' ? '120' : '64'}
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="loaderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#34D399" />
              <stop offset="100%" stopColor="#047857" />
            </linearGradient>
          </defs>
          <circle cx="32" cy="32" r="28" stroke="url(#loaderGrad)" strokeWidth="6" strokeLinecap="round" strokeDasharray="140" strokeDashoffset="100" />
          <circle cx="32" cy="32" r="16" stroke="#10B981" strokeWidth="4" strokeLinecap="round" strokeDasharray="60" strokeDashoffset="30" opacity="0.7" style={{ transformOrigin: "center", animation: "spin-reverse 1.5s linear infinite" }} />
        </svg>
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
