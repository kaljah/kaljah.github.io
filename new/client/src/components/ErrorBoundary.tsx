import React, { type ErrorInfo, type ReactNode } from "react";
import { CircleAlert, RefreshCw } from "lucide-react";
import "./ErrorBoundary.css";
import { t } from "../i18n";

export interface ErrorBoundaryProps {
  children?: ReactNode;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(): Partial<ErrorBoundaryState> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console for debugging
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = (): void => {
    window.location.reload();
  };

  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="[min-height:100vh] [display:flex] [align-items:center] [justify-content:center] [padding:20px] [background:linear-gradient(135deg,_var(--color-ink-900)_0%,_var(--color-ink-800)_100%)]">
          <div className="[background:rgba(255,_255,_255,_0.05)] [backdrop-filter:blur(20px)] [border:1px_solid_rgba(255,_255,_255,_0.1)] [&&]:[border-radius:var(--radius-lg)] [padding:40px]! [max-width:600px] [width:100%] [text-align:center] [box-shadow:var(--shadow-raised)] [@media(max-width:768px)]:[padding:30px_20px]!">
            <div className="[color:var(--color-red-700)] [margin-bottom:24px] [animation:pulse_2s_ease-in-out_infinite]">
              <CircleAlert size="64" strokeWidth="2" aria-hidden="true" />
            </div>

            <h1 className="[font-size:var(--text-2xl)]! [font-weight:700]! [color:var(--text-primary)] [margin:0_0_16px_0] [@media(max-width:768px)]:[font-size:var(--text-xl)]!">{t("Something went wrong")}</h1>
            <p className="error-message">
              {t("We're sorry, but an unexpected error occurred. Please try reloading the page or contact support if the problem persists.")}
            </p>

            {Boolean(import.meta.env?.DEV) &&
              this.state.error && (
                <details className="[background:rgba(0,_0,_0,_0.3)] [border:1px_solid_rgba(255,_255,_255,_0.1)] [&&]:[border-radius:var(--radius-md)] [padding:16px] [margin-bottom:24px] [text-align:left] [&_summary]:[cursor:pointer] [&_summary]:[font-weight:600] [&_summary]:[color:var(--color-amber-700)] [&_summary]:[margin-bottom:12px] [&_summary]:[user-select:none] [&&]:[&_summary:hover]:[color:var(--color-legacy-fbbf24)]">
                  <summary>{t("Error Details (Development Only)")}</summary>
                  <div className="[margin-top:12px] [font-size:var(--text-base)] [color:rgba(255,_255,_255,_0.7)] [&_strong]:[color:var(--color-red-700)] [&_pre]:[background:rgba(0,_0,_0,_0.4)] [&_pre]:[padding:12px] [&_pre]:[border-radius:var(--radius-sm)] [&_pre]:[overflow-x:auto] [&_pre]:[margin-top:8px] [&_pre]:[font-size:var(--text-sm)] [&_pre]:[line-height:1.5] [&_pre]:[white-space:pre-wrap] [&_pre]:[word-wrap:break-word]">
                    <p>
                      <strong>{t("Error:")}</strong> {this.state.error.toString()}
                    </p>
                    {this.state.errorInfo && (
                      <pre>{this.state.errorInfo.componentStack}</pre>
                    )}
                  </div>
                </details>
              )}

            <div className="[display:flex] [gap:12px] [justify-content:center] [margin-bottom:24px] [@media(max-width:768px)]:[flex-direction:column]">
              <button className="error-btn primary" onClick={this.handleReload}>
                <RefreshCw size={16} aria-hidden="true" />
                {t("Reload Page")}
              </button>
              <button
                className="error-btn secondary"
                onClick={this.handleReset}
              >
                {t("Try Again")}
              </button>
            </div>

            <div className="[padding-top:24px] [border-top:1px_solid_rgba(255,_255,_255,_0.1)] [font-size:var(--text-base)] [color:var(--text-secondary)] [&_a]:[color:var(--color-green-700)] [&_a]:[text-decoration:none] [&&]:[&_a:hover]:[text-decoration:underline]">
              <p>
                {t("Need help? Contact support at")}{" "}
                <a href="mailto:support@example.com">{t("support@example.com")}</a>
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
