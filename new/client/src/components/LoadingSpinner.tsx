import React from "react";
import "./LoadingSpinner.css";

export interface LoadingSpinnerProps {
  size?: "small" | "medium" | "large" | string;
  fullScreen?: boolean;
  message?: React.ReactNode;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
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
      {message && (
        <div className="[font-family:inherit] [color:var(--text-primary,_var(--color-ink-900))] [font-size:var(--text-md)] [font-weight:600] [letter-spacing:0.5px] [animation:pulse-opacity_2s_infinite_ease-in-out]">
          {message}
        </div>
      )}
    </div>
  );

  return (
    <div
      className={
        fullScreen
          ? "[position:fixed] [top:0] [left:0] [right:0] [right:0] [bottom:0] [background:transparent] [display:flex] [flex-direction:column] [align-items:center] [justify-content:center] [gap:40px] [z-index:9999] [animation:fadeIn_0.5s_ease-out]"
          : "[&&]:[display:flex] [&&]:[flex-direction:column] [&&]:[align-items:center] [&&]:[justify-content:center] [&&]:[gap:24px] [padding:60px_40px] [&&]:[background:transparent] [border:none]"
      }
    >
      {content}
    </div>
  );
};

export default LoadingSpinner;
