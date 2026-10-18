# sub-FRONTEND-MOBILE-STACKS — Vue 3/Nuxt, Angular Signals, Tailwind/Shadcn, React Native, Jetpack Compose & SwiftUI

Use when writing frontend or mobile code in stacks beyond React/Next.js and Flutter, or when implementing design-system
styling with Tailwind CSS / Shadcn UI. Enforce the same strict typing rule everywhere: zero `any`, zero typecasting
(`as Type`), and explicit defined types/interfaces for all props, emits, state, and API models.

## 1. Vue 3 & Nuxt 3 (TypeScript) rules

- **Component authoring**: always use `<script setup lang="ts">`.
- **Strictly typed Props, Emits & Slots**:
  - Declare explicit interfaces: `interface Props { orderId: string; initialCount?: number }` with `withDefaults(defineProps<Props>(), { initialCount: 0 })`.
  - Declare typed emits: `const emit = defineEmits<{ save: [payload: OrderSaveDto]; cancel: [] }>()`.
- **Reactivity & State**:
  - Use `ref` for primitives and `reactive` (or `ref` consistently per repo convention) with explicit type parameters `ref<OrderStatus>('pending')`.
  - Never destructure a reactive object or Pinia store directly without `storeToRefs(store)` (breaks reactivity).
  - Use `computed` for derived state — never mutate state inside a `computed` getter.
  - Clean up side effects, timers, and listeners inside `onWatcherCleanup` / `onUnmounted`.
- **Nuxt 3**: use `useFetch` / `useAsyncData` (never raw `fetch` in setup causing double SSR + client requests); keep
  server secrets inside `runtimeConfig` (private) and expose only safe public keys in `runtimeConfig.public`.

## 2. Angular (Modern v17+ Standalone & Signals) rules

- **Standalone by default**: build standalone components, directives, and pipes; use lazy-loaded `loadComponent` / `loadChildren` routes.
- **Change detection & Signals**:
  - Set `changeDetection: ChangeDetectionStrategy.OnPush` on every component.
  - Prefer Angular **Signals** (`input.required<T>()`, `output<T>()`, `signal<T>()`, `computed()`) for synchronous local
    and derived UI state; use `effect()` sparingly only for DOM/external sync.
- **RxJS interop & memory safety**:
  - Use RxJS for asynchronous event streams and `HttpClient` pipelines (`switchMap` to cancel stale searches, `exhaustMap`
    to prevent double form submission).
  - Unsubscribe deterministically using `takeUntilDestroyed()` or the template `async` pipe — never leave raw `.subscribe()` leaks.
- **Forms**: use Strictly Typed Reactive Forms (`FormGroup<{ email: FormControl<string>; age: FormControl<number | null> }>`).

## 3. Tailwind CSS, CSS Variables & Shadcn/Radix UI rules

- **Design tokens over magic numbers**: define semantic CSS variables (`--background`, `--foreground`, `--primary`,
  `--destructive`, `--border`) in the theme config; avoid scattering arbitrary hex values (`bg-[#1a2b3c]`) across components.
- **Component variants**: use `cva` (`class-variance-authority`) + `cn` (`clsx` + `tailwind-merge`) with explicit
  TypeScript `VariantProps<typeof buttonVariants>` interfaces.
- **Accessibility & interactive states**: preserve Radix/headless ARIA attributes; always include `focus-visible:ring-2`,
  `disabled:pointer-events-none disabled:opacity-50`, and responsive layout classes (`min-w-0` on flex/grid children to prevent text truncation overflow).

## 4. React Native & Expo rules

- **List performance**: use `FlashList` or properly configured `FlatList` (`keyExtractor` returning stable string ID,
  `getItemLayout` when fixed-height, memoized item components) — never map large arrays inside a `ScrollView`.
- **Navigation & Deep Links**: type all route params strictly (`ReactNavigation.RootParamList` or Expo Router typed routes).
- **Platform nuances**: handle `KeyboardAvoidingView` (`padding` on iOS, `height`/native behavior on Android), safe area
  insets (`useSafeAreaInsets()`), and hardware back button behavior on Android.

## 5. Kotlin Android (Jetpack Compose, Hilt, Coroutines/Flow) rules

- **Unidirectional Data Flow (UDF)**: UI observes a single immutable `UiState` (`sealed interface` or `data class`) exposed
  as `StateFlow<ScreenUiState>` from a `@HiltViewModel` and collects it with `collectAsStateWithLifecycle()`.
- **Compose stability & hoisting**: hoist state out of stateless `@Composable` functions; pass `Modifier` as the first optional
  parameter (`modifier: Modifier = Modifier`); never pass `ViewModel` instances down into reusable child composables.
- **Coroutines**: launch work in `viewModelScope`; inject dispatchers (`@IoDispatcher`) rather than hardcoding `Dispatchers.IO`.

## 6. Swift & SwiftUI (iOS) rules

- **Modern concurrency**: use `async/await`, structured `Task` cancellation (`.task(id:)` view modifier automatically cancels
  on view disappear), and `@MainActor` for all UI state mutations.
- **State management**: `@Observable` classes (iOS 17+) or `@StateObject`/`@ObservedObject` with value-type structs and
  `enum` state machines. Avoid force-unwrapping (`!`) and `try!`; handle optionals and `throws` explicitly.
