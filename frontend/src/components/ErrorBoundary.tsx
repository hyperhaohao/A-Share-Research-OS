import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

/** Keeps a render error from blanking the whole app (任务书 §21 robustness). */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // structured console log; backend error reporting arrives in M28
    console.error("render error:", error.message, info.componentStack ?? "");
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="page">
          <p className="status-error">
            界面渲染出错 · Render error —{" "}
            <button type="button" className="control-btn" onClick={() => this.setState({ hasError: false })}>
              重试 / Retry
            </button>
          </p>
        </main>
      );
    }
    return this.props.children;
  }
}
