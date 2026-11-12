# Existing product guardian
Before proposing changes, inspect (read-only where possible): repository routing, component library, design tokens, form/modal/table patterns, auth permission checks, terminology, locales, API response/error conventions, mobile breakpoints, accessibility patterns, tests, and current architecture. Avoid broad repository scans of secrets or unrelated data.

Create a pattern inventory: `pattern -> where used -> accepted behavior -> defects -> recommendation`. Differentiate a design system inconsistency from an intentional role-specific design choice. Preserve variable naming, architecture, and coding conventions when coding is requested.

## Change decision
Prefer reuse. Add new pattern only if existing component cannot meet an evidenced need, with documented impact and migration scope. Propose deprecation/migration instead of silently replacing shared components. Keep changes narrowly scoped, use existing APIs, and avoid modifying backend security rules without explicit approval. For design-only tasks, do not edit code.

## Regression checks
Check all affected roles, navigation/deep links, legacy data, mobile breakpoints, keyboard focus, error copy, existing screens that reuse the component, and design-token consistency.
