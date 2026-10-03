import React from "react";
import { CircleAlert } from "lucide-react";
import "./ErrorBoundary.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console for debugging
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // You can also log error to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="[min-height:100vh] [display:flex]! [align-items:center] [justify-content:center] [padding:20px]! [background:linear-gradient(135deg,_var(--color-ink-900)_0%,_var(--color-ink-800)_100%)]!">
          <div className="error-boundary-card">
            <div className="[color:var(--color-red-700)]! [margin-bottom:24px]! [animation:pulse_2s_ease-in-out_infinite]!">
              <CircleAlert size="64" strokeWidth="2" aria-hidden="true" />
            </div>

            <h1 className="error-title">Something went wrong</h1>
            <p className="error-message">
              We're sorry, but an unexpected error occurred. Please try
              reloading the page or contact support if the problem persists.
            </p>

            {Boolean(import.meta.env?.DEV) &&
              this.state.error && (
                <details className="error-details">
                  <summary>Error Details (Development Only)</summary>
                  <div className="error-stack">
                    <p>
                      <strong>Error:</strong> {this.state.error.toString()}
                    </p>
                    {this.state.errorInfo && (
                      <pre>{this.state.errorInfo.componentStack}</pre>
                    )}
                  </div>
                </details>
              )}

            <div className="error-actions">
              <button className="error-btn primary" onClick={this.handleReload}>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                </svg>
                Reload Page
              </button>
              <button
                className="error-btn secondary"
                onClick={this.handleReset}
              >
                Try Again
              </button>
            </div>

            <div className="error-footer">
              <p>
                Need help? Contact support at{" "}
                <a href="mailto:support@example.com">support@example.com</a>
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
