# Contrast Compatibility Plan

## Goal

Ensure AgentGate remains readable and navigable across default, high-contrast, and reduced-motion environments.

## Compatibility Layers

1. Default theme: warm neutral surface with teal/amber accents.
2. High-contrast mode: stronger border and text contrast for risk states and controls.
3. Reduced motion mode: disable transitions/animations while preserving hierarchy.

## Implementation Notes

1. Use CSS media query `prefers-contrast: more` to increase contrast for borders, text, and risk badges.
2. Avoid color-only indicators by pairing text labels with severity styles.
3. Keep keyboard focus ring visible in every contrast mode.
