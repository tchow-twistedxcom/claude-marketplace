/**
 * React Error Boundary Template
 *
 * Catches JavaScript errors anywhere in child component tree,
 * logs them, and displays a fallback UI instead of crashing.
 *
 * Usage:
 *   <ErrorBoundary fallbackTitle="Dashboard">
 *     <YourComponent />
 *   </ErrorBoundary>
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log to console for debugging
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);

    // Call optional error handler
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      const { fallbackTitle = 'Component' } = this.props;
      const { error, errorInfo } = this.state;

      return (
        <div style={styles.container}>
          <div style={styles.content}>
            <h2 style={styles.title}>
              {fallbackTitle} Error
            </h2>
            <p style={styles.message}>
              Something went wrong loading this section.
            </p>

            {process.env.NODE_ENV === 'development' && error && (
              <details style={styles.details}>
                <summary style={styles.summary}>Error Details</summary>
                <pre style={styles.pre}>
                  {error.toString()}
                  {errorInfo?.componentStack}
                </pre>
              </details>
            )}

            <button onClick={this.handleRetry} style={styles.button}>
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '200px',
    padding: '20px',
    backgroundColor: '#fef2f2',
    borderRadius: '8px',
    border: '1px solid #fecaca'
  },
  content: {
    textAlign: 'center',
    maxWidth: '500px'
  },
  title: {
    color: '#dc2626',
    fontSize: '1.25rem',
    marginBottom: '8px'
  },
  message: {
    color: '#7f1d1d',
    marginBottom: '16px'
  },
  details: {
    textAlign: 'left',
    marginBottom: '16px',
    backgroundColor: '#fff',
    padding: '12px',
    borderRadius: '4px',
    border: '1px solid #e5e7eb'
  },
  summary: {
    cursor: 'pointer',
    fontWeight: 500,
    color: '#374151'
  },
  pre: {
    marginTop: '8px',
    fontSize: '12px',
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    color: '#6b7280'
  },
  button: {
    backgroundColor: '#dc2626',
    color: 'white',
    padding: '8px 16px',
    borderRadius: '6px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500
  }
};

export default ErrorBoundary;
