// Sentry init — strictly opt-in.
//
// Only fires if BOTH:
//   1. VITE_SENTRY_DSN is set at build time
//   2. @sentry/react is installed
//
// Both conditions must hold so dev runs and CI don't need the package. To
// enable in prod: `npm install @sentry/react` and set VITE_SENTRY_DSN.

export async function initSentry(): Promise<void> {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  try {
    // Dynamic import so the package is only required when DSN is set.
    // @vite-ignore + string-built path keeps Vite from statically resolving
    // an optional peer dep that isn't in package.json.
    const sentryModule = ["@sentry", "react"].join("/");
    const Sentry: any = await import(/* @vite-ignore */ sentryModule);
    Sentry.init({
      dsn,
      tracesSampleRate: 0.1,
      environment: import.meta.env.MODE,
      // Don't send default PII; we don't have user accounts yet
      sendDefaultPii: false,
    });
    if (import.meta.env.DEV) {
      console.log("[sentry] initialized frontend SDK");
    }
  } catch {
    // Package not installed — silently skip
    if (import.meta.env.DEV) {
      console.warn(
        "[sentry] VITE_SENTRY_DSN set but @sentry/react not installed; run `npm install @sentry/react` to enable",
      );
    }
  }
}
