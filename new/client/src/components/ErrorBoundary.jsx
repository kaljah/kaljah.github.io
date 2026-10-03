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
          <div className="[background:rgba(255,_255,_255,_0.05)]! [backdrop-filter:blur(20px)] [border:1px_solid_rgba(255,_255,_255,_0.1)]! [border-radius:var(--radius-lg)]! [padding:40px]! [max-width:600px]! [width:100%]! [text-align:center]! [box-shadow:var(--shadow-raised)]! [@media(max-width:768px)]:[padding:30px_20px]!">
            <div className="[color:var(--color-red-700)]! [margin-bottom:24px]! [animation:pulse_2s_ease-in-out_infinite]!">
              <CircleAlert size="64" strokeWidth="2" aria-hidden="true" />
            </div>

            <h1 className="[font-size:var(--text-2xl)]! [font-weight:700]! [color:var(--text-primary)]! [margin:0_0_16px_0]! [@media(max-width:768px)]:[font-size:var(--text-xl)]!">Something went wrong</h1>
            <p className="error-message">
              We're sorry, but an unexpected error occurred. Please try
              reloading the page or contact support if the problem persists.
            </p>

            {Boolean(import.meta.env?.DEV) &&
              this.state.error && (
                <details className="[background:rgba(0,_0,_0,_0.3)]! [border:1px_solid_rgba(255,_255,_255,_0.1)]! [border-radius:var(--radius-md)]! [padding:16px]! [margin-bottom:24px]! [text-align:left]! [&_summary]:[cursor:pointer]! [&_summary]:[font-weight:600]! [&_summary]:[color:var(--color-amber-700)]! [&_summary]:[margin-bottom:12px]! [&_summary]:[user-select:none]! [&_summary:hover]:[color:#fbbf24]!">
                  <summary>Error Details (Development Only)</summary>
                  <div className="[margin-top:12px]! [font-size:var(--text-base)]! [color:rgba(255,_255,_255,_0.7)]! [&_strong]:[color:var(--color-red-700)]! [&_pre]:[background:rgba(0,_0,_0,_0.4)]! [&_pre]:[padding:12px]! [&_pre]:[border-radius:var(--radius-sm)]! [&_pre]:[overflow-x:auto]! [&_pre]:[margin-top:8px]! [&_pre]:[font-size:var(--text-sm)]! [&_pre]:[line-height:1.5]! [&_pre]:[white-space:pre-wrap]! [&_pre]:[word-wrap:break-word]!">
                    <p>
                      <strong>Error:</strong> {this.state.error.toString()}
                    </p>
                    {this.state.errorInfo && (
                      <pre>{this.state.errorInfo.componentStack}</pre>
                    )}
                  </div>
                </details>
              )}

            <div className="[display:flex]! [gap:12px] [justify-content:center] [margin-bottom:24px]! [@media(max-width:768px)]:[flex-direction:column]">
              <button className="[padding:12px_24px]! [border:none]! [border-radius:var(--radius-md)]! [font-size:var(--text-md)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.2s_ease]! [display:flex]! [align-items:center]! [gap:8px]! [&.primary]:[background:var(--color-green-700)]! [&.primary]:[color:white]! [&.primary:hover]:[background:var(--color-green-600)]! [&.primary:hover]:[transform:translateY(-2px)]! [&.primary:hover]:[box-shadow:0_4px_12px_rgba(16,_185,_129,_0.3)]! [&.secondary]:[background:rgba(255,_255,_255,_0.1)]! [&.secondary]:[color:var(--text-primary)]! [&.secondary]:[border:1px_solid_rgba(255,_255,_255,_0.2)]! [&.secondary:hover]:[background:rgba(255,_255,_255,_0.15)]! [@media(max-width:768px)]:[width:100%]! [@media(max-width:768px)]:[justify-content:center]! primary" onClick={this.handleReload}>
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
                className="[padding:12px_24px]! [border:none]! [border-radius:var(--radius-md)]! [font-size:var(--text-md)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.2s_ease]! [display:flex]! [align-items:center]! [gap:8px]! [&.primary]:[background:var(--color-green-700)]! [&.primary]:[color:white]! [&.primary:hover]:[background:var(--color-green-600)]! [&.primary:hover]:[transform:translateY(-2px)]! [&.primary:hover]:[box-shadow:0_4px_12px_rgba(16,_185,_129,_0.3)]! [&.secondary]:[background:rgba(255,_255,_255,_0.1)]! [&.secondary]:[color:var(--text-primary)]! [&.secondary]:[border:1px_solid_rgba(255,_255,_255,_0.2)]! [&.secondary:hover]:[background:rgba(255,_255,_255,_0.15)]! [@media(max-width:768px)]:[width:100%]! [@media(max-width:768px)]:[justify-content:center]! secondary"
                onClick={this.handleReset}
              >
                Try Again
              </button>
            </div>

            <div className="[padding-top:24px]! [border-top:1px_solid_rgba(255,_255,_255,_0.1)]! [font-size:var(--text-base)]! [color:var(--text-secondary)]! [&_a]:[color:var(--color-green-700)]! [&_a]:[text-decoration:none]! [&_a:hover]:[text-decoration:underline]!">
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
