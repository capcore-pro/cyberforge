import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Empêche un crash React de faire écran blanc — propose de recharger.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[CyberForge] Erreur interface", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-cyber-bg p-8 text-center">
          <p className="text-sm font-bold uppercase tracking-wider text-red-400">
            Erreur interface
          </p>
          <p className="max-w-md text-xs text-cyber-muted">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className="cyber-generate-btn"
            onClick={() => window.location.reload()}
          >
            Recharger l&apos;application
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
