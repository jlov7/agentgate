# Motion Guide

## Motion Principles

1. Motion should explain state transitions, not decorate pages.
2. Keep durations short (`150-300ms`) for most interactions.
3. Use easing that settles quickly (`ease-out`) for operational clarity.

## Approved Motion Patterns

1. Page enter: subtle fade-up used once on initial render.
2. Step reveal: timeline items fade from low opacity to full opacity.
3. Command palette: quick opacity transition for open/close.

## Accessibility Requirement

Honor `prefers-reduced-motion: reduce` by disabling non-essential animation and transitions.
