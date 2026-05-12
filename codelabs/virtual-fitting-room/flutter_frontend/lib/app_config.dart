class AppConfig {
  // Backend URL.
  //
  // Default is a same-origin relative path: the Go backend serves this Flutter
  // build at `/`, so calls to `/api/...` hit the API on the same host and port.
  // Works identically on local dev, Cloud Shell Web Preview, and Cloud Run —
  // no editing needed.
  //
  // Override at build time with --dart-define=ADK_BACKEND_URL=https://your-host/api
  // if you need to point at a different backend.
  static const String adkBackendUrl = String.fromEnvironment(
    'ADK_BACKEND_URL',
    defaultValue: '/api',
  );
}
