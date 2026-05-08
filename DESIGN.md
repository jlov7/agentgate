# AgentGate Design System Contract

## Design Direction

AgentGate uses a Containment Cockpit visual system: cinematic at the public front door, restrained and dense in the enterprise console. The interface should feel machined, calm, and operational rather than playful or decorative.

## Design Inputs

- Taste Skill is used for judgment: strong hierarchy, no generic SaaS sameness, no empty visual calories.
- Impeccable is used as a hard scanner: if it flags AI-design tells, the design is not done.
- Awesome Design references are used as comparator libraries, not brand templates. The current pass pulled `linear.app`, `sentry`, and `superhuman` references for product density, proof framing, restrained motion, and premium software pacing without inheriting their palettes.

## Typography

- Primary UI font: Geist Sans.
- Numeric and evidence font: Geist Mono.
- Use tabular figures for metrics, timestamps, request counts, and latency.
- Use sentence case for headings and labels.
- Avoid oversized type inside dashboards; reserve display scale for the public product front door.

## Color

- Use OKLCH tokens.
- Base: graphite and bone neutrals with slight green tint.
- Primary accent: verdigris, used sparingly for safe action and active control state.
- Risk palette: amber, red, and blue only for semantic state.
- Banned: purple/blue AI gradients, neon glows, pure black, pure white, and decorative gradient text.

## Layout

- Public pages may use asymmetric cinematic composition.
- Console pages use dense but readable operational grids.
- Cards are only for discrete objects or tools. Do not put cards inside cards.
- Avoid generic equal 3-column feature grids.
- Use full-width bands and unframed layouts for page sections.

## Motion

- Motion is purposeful and restrained.
- Animate only transform and opacity.
- Respect reduced-motion settings globally.
- Use motion to reveal state transitions, command-palette changes, and risk deltas, not as background spectacle.

## Components

- Buttons use clear icon/text pairing where the command benefits from an icon.
- Risk badges use semantic color plus text. Never rely on color alone.
- Timeline rows show decision, tool, actor, timestamp, and evidence correlation.
- Empty states must name the missing data and provide the next safe action.
- Error states must explain what failed, why it matters, and how to retry or recover.

## Absolute Bans

- Side-stripe borders on cards, alerts, or list items.
- Decorative glassmorphism as the default surface.
- Placeholder people, fake generic company names, and round-number telemetry.
- Buttons or links that go nowhere.
- Console browser errors on primary routes.
