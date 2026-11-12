# pm-ai-shipping — moved to product-engineering

The AI Shipping Kit is maintained in [phuryn/product-engineering](https://github.com/phuryn/product-engineering), in its `ai-shipping` plugin, with the release gate, the test harness and the independent review it grew into. Each skill and command here keeps its name and only says where it went, so an agent that loads one can tell you.

## Install it there

```bash
claude plugin marketplace add phuryn/product-engineering
claude plugin install ai-shipping@product-engineering
```

Then turn off `pm-ai-shipping` here, so the two don't load side by side. Other agents: [the repository's README](https://github.com/phuryn/product-engineering#install).

## Skills (3)

- [`code-review`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/code-review)
- [`intended-vs-implemented`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/intended-vs-implemented)
- [`shipping-artifacts`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/shipping-artifacts)

## Commands (5)

- `/ship-check`, now the [`ship-check`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/ship-check) skill
- `/document-app`, now the [`document-app`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/document-app) skill
- `/derive-tests`, now the [`derive-tests`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/derive-tests) skill
- `/security-audit-static`, now the [`security-audit-static`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/security-audit-static) skill
- `/performance-audit-static`, now the [`performance-audit-static`](https://github.com/phuryn/product-engineering/tree/main/ai-shipping/skills/performance-audit-static) skill
