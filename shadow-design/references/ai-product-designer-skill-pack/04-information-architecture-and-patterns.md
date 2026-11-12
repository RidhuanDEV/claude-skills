# Information architecture and interaction pattern library
Start from tasks and mental models: task inventory, navigation labels in the user's language, hierarchy, object relationships, cross-role access, and search/filter behavior. Keep navigation depth reasonable for product complexity; no arbitrary universal number.

## Pattern selection
- Tables for comparable structured records with sort/filter, visible selection state, bulk actions and responsive alternatives.
- Master-detail for inspection-heavy tasks; card grids for exploratory visual choices.
- Wizards only when users benefit from chunking coupled sequential steps; show progress, review and save-resume where warranted.
- Inline validation where feedback improves correction, with clear summary on submit; do not validate prematurely.
- Undo when reversible and safe; explicit confirm for costly irreversible actions.
- Permission prompts just-in-time with clear purpose; avoid repeated nagging.
- Empty state: explain why empty, meaningful action, permissions and filters; differentiate no results vs no data vs network error.
- Search: visible scope, sensible defaults, resilient zero-results state; preserve relevant filters/back navigation.
- Onboarding: reach first value early; progressive disclosure rather than compulsory tutorial.

## Cognitive principles
Recognition over recall, visibility of system status, error prevention, consistency, mental models, progressive disclosure, information scent, perceptible feedback, and appropriate Fitts/Hick tradeoffs. Heuristics guide review, not guarantee empirical success.
