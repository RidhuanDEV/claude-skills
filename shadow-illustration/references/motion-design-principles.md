# Motion design and frame-based export

Storyboard the initial state, anticipation, key action, follow-through and settled composition. Use staging, timing, spacing, easing, arcs, and purposeful secondary action. Keep the task signal readable. Avoid overstretching a mascot's proportions, using simultaneous motions that fight for focus, or looping a celebration behind repeated app interactions.

For a wave, place shoulder, elbow and wrist pivots where the arm segments meet. Check shoulder/upper-arm overlap, wrist orientation and hand silhouette throughout the arc. Inspect both extremes and an intermediate frame for gaps and abrupt flips. Avoid rotating an isolated hand when an elbow and wrist move together.

Define when motion begins, loops, pauses, stops or resets. Loop a pending state only while it remains pending. Pair reduced motion with a meaningful still and equivalent app feedback. For SVG/CSS verify transform origin and reduced-motion behavior in the actual component. Avoid motion that blocks or delays an action.

For spritesheets, agree frame size, order, origin, timing, padding and atlas metadata with the consumer. Render the atlas with the project's player and inspect boundaries for bleeding. For GIF check palette/alpha tradeoffs and timing in the target; deliver a suitable still alongside it if required.

Measure runtime performance only when execution scope allows. Capture observed timestamps and frames, and separate player observation from real device performance.
