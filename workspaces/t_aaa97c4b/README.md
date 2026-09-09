# Hermes Design System

> Build consistent, beautiful interfaces with a comprehensive token and component library.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Components](https://img.shields.io/badge/components-18-brightgreen)
![Tokens](https://img.shields.io/badge/tokens-85+-orange)

## Overview

Hermes is a production-ready design system that provides everything you need to build consistent, accessible, and beautiful user interfaces. It includes a comprehensive design token system, 18+ UI components, framework integrations, and extensive documentation.

## Features

- **85+ Design Tokens** — Color, typography, spacing, elevation, border radius, breakpoints, transitions, and z-index
- **18 Components** — Buttons, Cards, Badges, Inputs, Alerts, Modals, Avatars, Tabs, Tooltips, Progress, Toggles, Breadcrumbs, Pagination, Tables, Skeletons, Accordions, Toasts
- **Dark Mode** — Built-in dark theme with CSS custom properties
- **Responsive** — Mobile-first design with responsive breakpoints
- **Accessible** — WCAG 2.1 AA compliant components
- **Framework Agnostic** — Integration guides for React, Vue, and Vanilla JS
- **Search** — Full-text search across all documentation
- **Versioned** — Changelog and migration guides

## Quick Start

### Via CDN

```html
<link rel="stylesheet" href="https://cdn.hermes-ds.com/core/tokens.css">
<link rel="stylesheet" href="https://cdn.hermes-ds.com/core/components.css">
<script src="https://cdn.hermes-ds.com/core/hermes.js"></script>
```

### Via npm

```bash
npm install @hermes-design-system/core
```

```javascript
import '@hermes-design-system/core/dist/tokens.css';
import '@hermes-design-system/core/dist/components.css';
```

## Project Structure

```
hermes-design-system/
├── index.html              # Documentation site
├── src/
│   ├── styles/
│   │   ├── tokens.css      # CSS custom properties (design tokens)
│   │   ├── main.css        # Layout, typography, global styles
│   │   └── components.css  # Component styles
│   ├── data/
│   │   └── tokens.json     # Token dictionary (source of truth)
│   ├── components/         # Component source files
│   └── app.js              # Interactive functionality
├── package.json
└── README.md
```

## Design Tokens

### Color

| Category | Tokens |
|----------|--------|
| Brand | primary, primaryLight, primaryDark, secondary, tertiary, accent |
| Neutral | white, gray50–gray900, black |
| Semantic | success, warning, error, info (+ light variants) |

### Typography

| Category | Tokens |
|----------|--------|
| Font Family | sans, mono, display |
| Font Size | xs (12px) – 6xl (60px) |
| Font Weight | regular (400) – bold (700) |
| Line Height | tight, normal, relaxed |
| LetterSpacing | tighter – wider |

### Spacing

A 0–24 spacing scale (0–6rem) for consistent margins, paddings, and gaps.

### Elevation

Six elevation levels (0–5) for shadow depth hierarchy.

### Border Radius

Seven radius values from none to full (9999px).

### Breakpoints

sm (640px), md (768px), lg (1024px), xl (1280px), 2xl (1536px)

## Components

| Component | Category | Description |
|-----------|----------|-------------|
| Buttons | Form | Primary, secondary, outline, ghost, danger variants |
| Cards | Layout | Basic, interactive, highlighted card layouts |
| Badges | Display | Status badges with color and style variants |
| Inputs | Form | Text inputs, textareas, selects with validation states |
| Alerts | Feedback | Success, warning, error, info contextual messages |
| Modals | Overlay | Dialog overlays with header, body, footer |
| Avatars | Display | Initials-based avatars with size and status variants |
| Tabs | Navigation | Tabbed content panels |
| Tooltips | Feedback | Hover tooltip overlays |
| Progress | Feedback | Progress bars with determinate/indeterminate states |
| Toggles | Form | On/off toggle switches |
| Breadcrumbs | Navigation | Hierarchical page navigation |
| Pagination | Navigation | Page number navigation controls |
| Tables | Display | Structured data tables |
| Skeletons | Feedback | Loading placeholder animations |
| Accordions | Layout | Collapsible content panels |
| Toasts | Feedback | Brief notification messages |

## Framework Integration

### React

```bash
npm install @hermes-design-system/react
```

```tsx
import { HermesProvider, Button, Card } from '@hermes-design-system/react';

function App() {
  return (
    <HermesProvider theme="light">
      <Card>
        <h2>Welcome</h2>
        <Button variant="primary">Get Started</Button>
      </Card>
    </HermesProvider>
  );
}
```

### Vue

```bash
npm install @hermes-design-system/vue
```

```vue
<template>
  <HermesCard>
    <h2>Welcome</h2>
    <HermesButton variant="primary">Get Started</HermesButton>
  </HermesCard>
</template>

<script setup>
import { HermesCard, HermesButton } from '@hermes-design-system/vue';
</script>
```

### Vanilla JS

```javascript
import Hermes from '@hermes-design-system/core';

const hermes = Hermes.init({ theme: 'light' });
hermes.toast.success('Hello from Hermes!');
```

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT © 2026 Hermes Design System

## Links

- [Documentation Site](https://hermes-ds.com)
- [GitHub Repository](https://github.com/itsPremkumar/hermes-design-system)
- [npm Package](https://www.npmjs.com/package/@hermes-design-system/core)
- [Figma Kit](https://figma.com/hermes-design-system)
