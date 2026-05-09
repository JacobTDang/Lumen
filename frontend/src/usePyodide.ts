// Lazy-load Pyodide (Python compiled to WebAssembly) on first use.
// ~3MB initial download from CDN, cached after.
//
// We don't bundle pyodide via npm because it pulls megabytes into the
// build artifact even when unused. CDN load happens only when the user
// opens a code editor and clicks Run for the first time.

import { useCallback, useState } from "react";

const PYODIDE_VERSION = "0.27.0";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export interface PyodideState {
  pyodide: any | null;
  loading: boolean;
  error: string | null;
}

export function usePyodide() {
  const [state, setState] = useState<PyodideState>({
    pyodide: null,
    loading: false,
    error: null,
  });

  const load = useCallback(async () => {
    if (state.pyodide || state.loading) return;
    setState({ pyodide: null, loading: true, error: null });

    try {
      // Inject the pyodide.js loader script if not already present.
      // window.loadPyodide is set by that script.
      if (!(window as any).loadPyodide) {
        await new Promise<void>((resolve, reject) => {
          const s = document.createElement("script");
          s.src = `${PYODIDE_INDEX_URL}pyodide.js`;
          s.async = true;
          s.onload = () => resolve();
          s.onerror = () => reject(new Error("Pyodide CDN script failed to load"));
          document.head.appendChild(s);
        });
      }
      const py = await (window as any).loadPyodide({
        indexURL: PYODIDE_INDEX_URL,
      });
      setState({ pyodide: py, loading: false, error: null });
    } catch (e) {
      setState({
        pyodide: null,
        loading: false,
        error: e instanceof Error ? e.message : "Pyodide load failed",
      });
    }
  }, [state.pyodide, state.loading]);

  return { ...state, load };
}
