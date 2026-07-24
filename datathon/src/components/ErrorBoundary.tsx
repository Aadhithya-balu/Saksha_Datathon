import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  fallbackLabel?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[ErrorBoundary] ${this.props.fallbackLabel ?? 'Page'} crashed:`, error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-[#D4820A] mb-4" />
          <h2 className="text-sm font-mono font-bold text-[#E8EDF5] uppercase tracking-wider mb-2">
            Module Runtime Error
          </h2>
          <p className="text-[10px] font-mono text-[#6A7A96] max-w-md mb-4">
            {this.props.fallbackLabel
              ? `The ${this.props.fallbackLabel} module encountered an unexpected error.`
              : 'This module encountered an unexpected error.'}
          </p>
          {this.state.error && (
            <pre className="text-[9px] font-mono text-[#C94A2A] bg-[#C94A2A]/5 border border-[#C94A2A]/20 rounded p-3 max-w-lg w-full overflow-auto mb-4">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={this.handleReset}
            className="px-4 py-1.5 bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 text-[#1E6FD9] font-mono text-[10px] uppercase tracking-wider rounded hover:bg-[#1E6FD9]/25 transition-colors cursor-pointer"
          >
            Retry Module Load
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
