import React, { ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("App crash caught by ErrorBoundary:", error, info);
  }

  handleRetry = () => {
    this.setState({ error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1A1A1A",
          color: "#E8E8E8",
          fontFamily: "Inter, sans-serif",
          padding: 24,
        }}
      >
        <div
          style={{
            maxWidth: 480,
            width: "100%",
            background: "#242424",
            border: "1px solid #2A2A2A",
            borderRadius: 8,
            padding: 24,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 500,
              letterSpacing: "0.05em",
              color: "#6B6B6B",
              textTransform: "uppercase",
              marginBottom: 12,
            }}
          >
            Something went wrong
          </div>
          <div style={{ fontSize: 14, lineHeight: 1.5, marginBottom: 16 }}>
            The page hit an unexpected error and stopped rendering. The
            details below may help diagnose what broke.
          </div>
          <pre
            style={{
              fontSize: 11,
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              background: "#1A1A1A",
              border: "1px solid #2A2A2A",
              borderRadius: 4,
              padding: 12,
              overflowX: "auto",
              color: "#fca5a5",
              marginBottom: 16,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {error.message || "Unknown error"}
          </pre>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={this.handleRetry}
              style={{
                fontSize: 13,
                padding: "8px 14px",
                color: "#FFFFFF",
                background: "#2563EB",
                border: "1px solid #2563EB",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <button
              onClick={this.handleReload}
              style={{
                fontSize: 13,
                padding: "8px 14px",
                color: "#E8E8E8",
                background: "transparent",
                border: "1px solid #2A2A2A",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
