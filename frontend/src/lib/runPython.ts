// Execute Python code via Pyodide and capture stdout / stderr / exception.
// Pyodide doesn't natively support cancellation, so an infinite loop will
// hang the tab. For MVP we accept that risk — most LeetCode-style runs
// finish in milliseconds.

export interface RunResult {
  stdout: string;
  stderr: string;
  error: string | null;
  durationMs: number;
}

export async function runPython(pyodide: any, code: string): Promise<RunResult> {
  const start = performance.now();
  let stdout = "";
  let stderr = "";

  // Pyodide stdout/stderr APIs accept a `batched` callback that fires per
  // line. Re-bind on every run to clear state from prior executions.
  pyodide.setStdout({
    batched: (s: string) => { stdout += s + "\n"; },
  });
  pyodide.setStderr({
    batched: (s: string) => { stderr += s + "\n"; },
  });

  let error: string | null = null;
  try {
    await pyodide.runPythonAsync(code);
  } catch (e) {
    // Pyodide wraps Python exceptions; the .message contains the traceback
    error = e instanceof Error ? e.message : String(e);
  }

  return {
    stdout,
    stderr,
    error,
    durationMs: Math.round(performance.now() - start),
  };
}
