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
    <>
      <div className={`video-loader-container ${sizeClass}`} style={{ marginBottom: '1rem' }}>
        <video
          ref={videoRef}
          src={animationVideo}
          autoPlay
          loop
          muted
          playsInline
          style={{
            width: size === 'large' ? '160px' : '100px',
            height: size === 'large' ? '160px' : '100px',
            objectFit: "contain",
          }}
        />
      </div>
    </>
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
