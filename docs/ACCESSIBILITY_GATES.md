# Accessibility Gates

## Release Acceptance Gates

1. Keyboard-only navigation works across onboarding, sandbox, replay, incident, and rollout workflows.
2. Dialogs and overlays trap focus and restore it on close.
3. Every async workflow surface exposes `aria-live` updates for status changes.
4. Reduced motion preference disables non-essential animation.
5. High-contrast preference preserves readable controls and risk states.
6. A11y smoke tests run in CI and block release when failing.

## Verification Commands

```bash
make a11y-smoke
.venv/bin/pytest -q tests/test_accessibility_assets.py
```

## Scope

These gates are minimum release requirements; they complement broader WCAG 2.2 audits and moderated usability sessions.
