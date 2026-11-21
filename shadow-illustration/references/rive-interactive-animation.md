# Rive and interactive motion handoff

Use when an input-driven animation is needed and the project has a compatible Rive workflow. Check authoring/export access and actual runtime versions separately. When only a brief is feasible, deliver the state and interaction specification with art source, and leave the native export and playback checks open.

1. List the app states, data inputs and transition triggers. Name the artboard and state machine or binding surfaces from existing source when available.
2. Specify initial state, guards, interrupted transitions, reset, looping, and fallback. Keep app success/failure in application state. The illustration can reflect it through approved inputs.
3. Export through the supported tool and inspect the real runtime with representative inputs, fast toggles, invalid or missing input as relevant, pause/resume, and reduced motion.
4. Handoff the editable authoring source where supported, exported path, bindings, target runtime/version, static fallback, and actual input/output evidence.

The [source register](open-source-source-register.md) distinguishes runtime code from editor and service terms.
