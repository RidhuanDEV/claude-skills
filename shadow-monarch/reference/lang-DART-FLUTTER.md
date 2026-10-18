# Dart / Flutter

Target the project's Flutter/Dart SDK (`pubspec.yaml` environment constraints). Sound null safety is mandatory. Follow Effective Dart and `flutter_lints`/`very_good_analysis`.

## 1. Project structure

Feature-first, layered:
```text
lib/
  main.dart / bootstrap.dart         env setup, DI, error handlers, runApp
  app/                               router, theme (design tokens), localization
  features/<feature>/
    presentation/ (screens, widgets, controllers/view-models)
    domain/       (entities, value objects, use cases, repository interfaces)
    data/         (DTOs with fromJson/toJson, API clients, repository implementations, local storage)
  core/ (network, errors, utils with no business logic)
```
- Widgets render; controllers/notifiers/blocs hold UI state and call use cases; repositories own data access and caching.
- Models immutable (`final` fields, `copyWith`, `freezed` for unions/equality, `json_serializable` for JSON). Never pass raw `Map<String, dynamic>` around the app.

## 2. State management

Use the project's choice consistently — **Riverpod** or **Bloc/Cubit** are common production choices; Provider for simpler apps.
- `setState` only for local, ephemeral widget state.
- Model async state explicitly (`AsyncValue` in Riverpod, sealed state classes in Bloc: initial/loading/success/failure).
- Do not put business logic in widgets; do not mutate state objects in place.
- Dispose resources: `TextEditingController`, `AnimationController`, `ScrollController`, `FocusNode`, `StreamSubscription`, timers —
  in `dispose()` (or use providers with auto-dispose).
- After `await` in a `State`, check `if (!mounted) return;` before using `context` or calling `setState`.

## 3. Widgets and performance

- Small, composable widgets; prefer `StatelessWidget` + external state; extract widgets rather than helper methods returning widgets (better rebuild isolation).
- `const` constructors wherever possible. Avoid heavy work in `build()` — it may run every frame.
- `ListView.builder`/`SliverList` for long lists; keys (`ValueKey(id)`) for reorderable/stateful items.
- Images: cache (`cached_network_image`), size appropriately (`cacheWidth`), placeholders and error builders.
- Heavy computation off the UI isolate: `Isolate.run()` / `compute()`. Profile with DevTools in profile mode (not debug) — target 60/120 fps, watch jank.
- `RepaintBoundary` only where profiling shows benefit.

## 4. Async and errors

- `Future`/`async`/`await`; never ignore futures silently (lint `unawaited_futures`; use `unawaited()` only intentionally).
- Streams: cancel subscriptions; prefer `StreamBuilder`/state-management integrations over manual listeners.
- Typed failures: map exceptions from the data layer into domain failures (sealed classes / `Either`-like results) — do not leak `DioException`/`SocketException` to UI.
- Global error handling: `FlutterError.onError`, `PlatformDispatcher.instance.onError`, and crash reporting (Crashlytics/Sentry) with PII scrubbed.
- Networking: `dio` or `http` with timeouts (connect/receive), interceptors for auth refresh (single-flight refresh to avoid token stampedes), retry only idempotent requests,
  cancellation (`CancelToken`) when screens are disposed.

## 5. UX specifics (see DESIGN.md)

Material 3 / Cupertino consistently; theme via `ThemeData`/`ColorScheme` tokens, no hardcoded colors/sizes in widgets; respect text scaling
(`MediaQuery.textScalerOf`) and test at large font sizes; `Semantics` for custom widgets and icon buttons; minimum 48dp touch targets;
safe areas and keyboard insets; responsive layouts with `LayoutBuilder` for tablets/web/desktop; loading/empty/error/offline states; localization via `intl`/ARB files.

## 6. Security and data

- Never embed secrets/API keys that grant privileged access in the app — the binary can be decompiled. Proxy privileged calls through your backend.
- Tokens in `flutter_secure_storage` (Keychain/Keystore), never `SharedPreferences`. Clear on logout.
- HTTPS only; consider certificate pinning for high-risk apps (with a rotation plan). Validate deep links and never trust client-side checks for authorization.
- Obfuscate release builds (`--obfuscate --split-debug-info`) — this raises effort, it is not security.
- Minimize permissions; explain them in-context; handle denial gracefully.
- Local DB (drift/sqflite/Isar/Hive): parameterized queries, encryption for sensitive data, migrations versioned.
- Logs: no tokens/PII; use `debugPrint`/a logger disabled or reduced in release.

## 7. Navigation and platform

`go_router` (or the project's router) with typed routes, auth redirects, deep-link handling. Platform channels/FFI isolated behind interfaces;
handle all platforms the app ships (Android, iOS, web, desktop) — check `kIsWeb`/`Platform` carefully (`dart:io` is unavailable on web).
Money with integer minor units/`decimal` package; dates in UTC internally, localized at display.

## 8. Testing

- Unit tests (`test`) for domain/use cases/notifiers/blocs (`bloc_test`, Riverpod `ProviderContainer` overrides).
- Widget tests (`flutter_test`: `pumpWidget`, `find.bySemanticsLabel`, `tester.tap`, `pumpAndSettle` with care).
- Golden tests for key components (pin fonts/platform to avoid flakiness).
- Integration tests (`integration_test`) for critical journeys on real devices/emulators.
- Mocks with `mocktail`; fake repositories over deep mocking.

## 9. Tooling

`dart format` · `flutter analyze` with strict lints (`strict-casts`, `strict-raw-types`) · `build_runner` for codegen (commit or regenerate consistently) ·
flavors/`--dart-define-from-file` for environments (no secrets) · CI builds for each target platform · `flutter pub outdated` and dependency review
(check package maintenance, platform support, null safety).

## 10. Common mistakes to catch

Business logic and API calls inside `build()` or widgets · missing `dispose()` · using `context` after `await` without `mounted` check ·
`setState` for app-wide state · non-`const` widgets everywhere causing rebuilds · `ListView(children: [...])` for huge lists · heavy JSON parsing on the UI isolate ·
tokens in `SharedPreferences` · secrets in the app bundle · `dynamic`/raw maps instead of models · swallowed exceptions in `catch (_) {}` ·
ignoring text scaling and semantics · hardcoded colors/sizes · `dart:io` imports breaking web builds · untested error/offline states.
