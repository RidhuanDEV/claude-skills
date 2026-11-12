# Accessibility, responsive UI, and content design
Target WCAG 2.2 AA unless project specifies stricter. Use semantic structure, operable keyboard flows, visible focus, predictable tab and focus order, appropriately named controls, error association and announcement, text alternatives, adequate contrast, and user-respecting motion settings. Validate target size requirements against actual WCAG criteria; do not assume a single pixel rule applies universally.

Test at narrow mobile viewport, tablet, desktop, browser zoom up to 400%, large text, keyboard-only, screen reader flows, touch use, reduced motion, light/dark if supported, and long localized labels. Reflow information instead of hiding essential actions. Wide data tables may require deliberate horizontal scroll, summary mode, or row details; label alternatives clearly.

Content design: plain language with user vocabulary; verb-led CTAs; informative headings; no misleading urgency; errors describe what happened, whether work is safe, and the next possible action. Use consistent naming for states/actions. Dates, currency and timezone must match context. Avoid raw HTTP status/error stacks in user-facing copy.

Checklist: can users find the action, understand the result, recover after error, complete using keyboard/screen reader, and understand uncertainty without color alone?
