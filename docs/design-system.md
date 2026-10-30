# Recruit Lens Design System & Component Guidelines

## 1. Design Philosophy
Recruit Lens implements a calm, enterprise-grade, data-dense interface inspired by modern engineering tools like Linear and Vercel. Decorative illustrations, gradients, and emojis in UI chrome are strictly prohibited. Visual cues combine color, typography, and SVG iconography so color is never the sole information carrier.

---

## 2. Color Tokens & Contrast Compliance

### Dark Theme (Primary Default)
- **Canvas (Background):** `#0B0F17`
- **Surface (Cards / Panels):** `#111827`
- **Subtle (Hover / Inputs / Wells):** `#1F2937`
- **Border Default:** `#374151`
- **Text Primary:** `#F9FAFB` (Contrast ratio $> 14:1$ on Canvas)
- **Text Secondary:** `#9CA3AF` (Contrast ratio $> 4.8:1$ on Canvas; WCAG 2.2 AA compliant)

### Primary Interactive Blue
- **Primary Button Background:** `#2563EB` (Tailwind `blue-600`) with `#FFFFFF` text.
- *Compliance Note:* Standard `#3B82F6` achieves only $3.8:1$ contrast against pure white text. `#2563EB` provides $> 4.5:1$ contrast ratio, satisfying WCAG 2.2 AA for normal body and control text.

### Semantic Tiers
Every tier badge is rendered as a pill with tinted background, border, light/dark text contrast, and an explicit SVG icon:
- **FastTrack:** Emerald (`#10B981` / `border-emerald-500/30`, icon: `<Check />`)
- **Interview:** Sky Blue (`#0EA5E9` / `border-sky-500/30`, icon: `<Circle />`)
- **Hold:** Amber (`#F59E0B` / `border-amber-500/30`, icon: `<Clock />`)
- **Reject:** Red (`#EF4444` / `border-red-500/30`, icon: `<X />`)

---

## 3. Typography & Sizing

- **Primary Font:** Inter (`font-sans`), clean geometric sans-serif for UI labels, tables, and narrative summaries.
- **Data & Monospace:** System monospace (`font-mono`) for candidate codes (`Candidate #6299`), scores, latency figures, timestamps, and citation IDs (`[c_01]`).
- **Hierarchy:**
  - Page Titles: `text-2xl font-bold tracking-tight`
  - Section Headers: `text-xs font-semibold uppercase tracking-wider`
  - Body / Tables: `text-xs leading-relaxed`
  - Metadata / Subtitles: `text-[11px] text-[var(--text-secondary)]`

---

## 4. Component Standards

### Global Navbar
- Height: Exact `56px` (`h-[56px]`), sticky top with surface background and 1px bottom border.
- Left: Recruit Lens brand mark (magnifying lens in blue tile) + Job selector dropdown button.
- Center: Quick navigation tabs (`Requisitions`, `Candidates`, `Dossier`, `Pipeline`, `Email Center`, `Audit Log`, `Analytics`, `Settings`).
- Right: Telemetry status dot (`Retrieval OK · BM25 + embeddings · p95 420 ms · Audit chain verified`), Blind screening switch (`role="switch"`, `aria-checked`), Theme toggle, and Recruiter profile indicator.

### Buttons & Interactive Controls
- Border Radius: `8px` (`rounded-lg` or `rounded-md`).
- Minimum Height: `36px` on desktop, `44px` minimum touch target on mobile viewports.
- Focus State: Visible high-contrast focus rings (`focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`).

### Citation Pills (`<CitationPill />`)
- Compact monospace button: `[c_01]`.
- Active styling: Blue highlight with border.
- Behavior: Keyboard focusable (`Tab`), activated with `Enter` or `Space`, triggers smooth scroll to the verbatim resume chunk in the evidence viewer and announces to assistive technologies via a hidden `role="status"` `aria-live="polite"` region.

### Circular Score Gauge (`<ScoreGauge />`)
- SVG circular meter (0–100) with `role="meter"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`.
- Color dynamically mapped to tier thresholds ($\ge 85$ emerald, $\ge 70$ sky, $\ge 55$ amber, $< 55$ red).

---

## 5. Accessibility (WCAG 2.2 AA)
1. **Perceivable:** High contrast on all text and controls; color is never the only indicator (icons + labels on all tier badges).
2. **Operable:** Full keyboard navigation support (arrow keys and enter across candidate rows, modal escape handlers, tabbed layouts).
3. **Understandable:** Plain-language glossary and clear contextual tooltips.
4. **Robust:** Semantic ARIA roles (`role="switch"`, `role="meter"`, `role="dialog"`, `role="status"`, `aria-live="polite"`). Reduced motion media query (`prefers-reduced-motion: reduce`) suppresses animations.
