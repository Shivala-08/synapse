# Synapse Frontend — Build Manual

**Hand this to Claude Code / Cursor as the frontend build spec.** It assumes
the dual-domain backend from the earlier manual is already wired up
(domain profiles, namespaced storage, mastery tracking, roadmap generation)
and exposed via FastAPI. This manual only covers the frontend.

**Why not keep Streamlit:** Streamlit is fine for the backend build phase,
but it fights you on glassmorphism, custom motion, and the "premium dark
product" feel you've already established in Comp U Serve. Build a proper
Next.js frontend that talks to the existing FastAPI backend instead of
extending Streamlit further. You already have this exact stack
(Next.js, GSAP, Lenis, Vanta.NET) - reuse it rather than learning a new one.

---

## 0. Design Plan (read this before building anything)

### Subject, audience, job
This is a personal cognition tool, not a SaaS product - the only user is
you. Its job is to make two things visible at a glance: **what you know**
(Second Brain graph) and **what you don't yet, and how urgently** (Exam
Prep mastery + roadmap). Everything in the design should serve legibility
under time pressure, not decoration.

### Design read
Reading this as: a dark premium product UI for a single power user, with a
restrained "synapse firing" indigo language, leaning toward glass panels on
a graphite-blue canvas, Clash Display for data numbers, Satoshi for body.

Dials: `DESIGN_VARIANCE: 6`, `MOTION_INTENSITY: 4`, `VISUAL_DENSITY: 6`.
One orchestrated motion moment (the signal pulse). Everything else quiet,
fast, and input-driven.

### Color - the token set
| Token | Hex | Role |
|---|---|---|
| `--bg` | `#0B0E13` | Base canvas - graphite-blue-black, not pure black |
| `--surface` | `rgba(255,255,255,0.04)` | Glass panel fill, always paired with blur |
| `--surface-solid` | `#12161D` | Opaque fallback where transparency is reduced |
| `--border` | `rgba(255,255,255,0.08)` | Hairline panel edges |
| `--signal` | `#7C9EFF` | Primary accent - "synapse firing" indigo, used for active states, links, the graph's edges |
| `--growth` | `#5EEAD4` | Mastery / strength indicator - muted teal, not green |
| `--attention` | `#F0A868` | Needs-revision indicator - warm amber, never red (deliberately non-alarming) |
| `--text` | `#E8EAF0` | Primary text |
| `--text-muted` | `#8B93A7` | Secondary text |
| `--danger` | `#E5484D` | Actual failures only (connection errors, ingest errors). Never used for mastery or revision signals. |

Color discipline:

- The indigo accent is brand-intentional. Execute it with restraint: one
  accent, harmonized graphite neutrals, no purple glow gradients, no
  gradient text on headers. Indigo marks active state, links, and the graph
  edges. Nothing else gets colored.
- Amber and teal are the only "judgment" colors in the whole UI. If
  something is not a mastery signal, it does not get colored, it stays
  `--text-muted`.
- `--danger` is reserved for real errors. A 0% mastery bar still renders at
  the amber end of the scale, never red.
- Color consistency lock: the accent used on a page is the accent used on
  the whole page. No section introduces a second accent.

### Type - 2 families
- **Display / data numbers:** Clash Display - your visual signature across
  projects. Self-host via @font-face (Fontshare woff2), `font-display: swap`.
- **Body / UI text:** Satoshi - same reasoning, consistency across your
  own portfolio. Self-host the same way.
- No monospace anywhere except actual code snippets in the Query Console
  and timing values that behave like data (latency, node ids).
- Italic is never used in display type. Display emphasis is weight or color,
  not a second family.

### Shape consistency lock
One radius scale, documented and followed everywhere:

- Panels, cards, the rail, side panels: `14px`
- Controls (buttons, inputs, segmented, chips): `10px`
- Status dots and live indicators: full circle

No mixed systems. Square cards next to pill buttons is broken design.

### Layout concept
Persistent left rail (domain switcher + nav), full-bleed main canvas per
section - not a grid of identical cards. Each section gets a layout
appropriate to its content, not the same card kit repeated:

```
┌──────────┬─────────────────────────────────────────┐
│          │                                          │
│  RAIL    │   MAIN CANVAS                            │
│          │   (shape changes per section - see below)│
│ Domain:  │                                           │
│ ● Second │                                           │
│   Brain  │                                           │
│ ○ Exam   │                                           │
│   Prep   │                                           │
│          │                                           │
│ ─────    │                                           │
│ Query    │                                           │
│ Graph    │                                           │
│ Revision │                                           │
│ Roadmap  │                                           │
│ Library  │                                           │
│          │                                           │
└──────────┴─────────────────────────────────────────┘
```

### The one bold element
A **signal pulse** - when a query resolves, a thin animated line travels
from the source node(s) in the graph to the answer panel, visualizing
"this answer came from these three nodes." This is the single
orchestrated motion moment. Everything else (hover states, panel
transitions) stays quiet and fast - no scattered fade-up animations per
card, no infinite loops, no marquees.

### Principles
1. Amber and teal are the only "judgment" colors in the whole UI - if
   something isn't a mastery signal, it doesn't get colored, it stays
   `--text-muted`.
2. The graph is never just a decoration - it's clickable everywhere it
   appears, including the small preview version in the sidebar.
3. No numbered eyebrows, no ALL-CAPS labels, no middle-dot meta strings.
   Section headers are plain sentence case. No `·` separators in meta
   strips; use line breaks, hairlines, or columns.
4. Em-dashes are banned everywhere in the UI, including body copy. Use
   periods, commas, or colons.
5. Every visible string is plain and functional. No filler verbs
   ("elevate", "seamless"), no fake-precise numbers, no cute micro-meta.

### Interaction states (all interactive elements)
- **Loading:** skeletal blocks shaped like the final layout. No generic
  circular spinners.
- **Empty:** composed empty states that say how to populate the view.
- **Error:** inline and contextual, in `--danger` only for real failures.
- **Tactile feedback:** buttons and chips shift down `1px` on `:active`.
- **Contrast:** all body text meets WCAG AA (4.5:1) against its surface.
  Button labels readable against their fill. Focus rings visible on
  `:focus-visible` for every interactive element.

---

## 1. Route Map (Next.js App Router)

```
/                       → redirects to /second-brain/query or last active domain
/[domain]/query         → Query Console (default view)
/[domain]/graph         → Knowledge Graph Explorer (full-bleed)
/[domain]/revision      → Revision Dashboard (exam-prep only)
/[domain]/roadmap       → Roadmap (exam-prep only)
/[domain]/library       → Document Library (both domains)
```

`[domain]` is `second-brain` or `exam-prep` (kebab-case segments that map
to the backend's `second_brain` / `exam_prep` domain ids). The left rail's
domain toggle just swaps this segment and re-fetches - no client-side
domain state duplication, the URL is the source of truth.

---

## 2. Component Specs

### 2.1 Left Rail (`components/Rail.tsx`)
- Two domain options at top, each showing a tiny live dot (green if that
  domain's collection responds to a quick probe, muted otherwise)
- Nav links below: Query · Graph · Revision · Roadmap · Library
- Revision and Roadmap links only render when `domain === 'exam-prep'`
- Persistent across all routes - lives in `app/[domain]/layout.tsx`
- On the graph route, the rail collapses to icon-only so the canvas gets
  the most screen space
- Footer: backend status + active model, small and quiet

### 2.2 Query Console (`app/[domain]/query/page.tsx`)
- Chat-style vertical scroll, your message right-aligned in a glass
  bubble, Synapse's answer left-aligned
- Each answer ends with a small horizontal strip of **source chips** -
  one chip per retrieved node/chunk, each linking to that node in the
  Graph Explorer (`/[domain]/graph?node=<id>`)
- On answer render, trigger the signal-pulse animation: draw a temporary
  SVG path from a tiny inline graph thumbnail (bottom-left of the answer
  bubble) toward the source chips, then fade after ~800ms
- Streaming: consume the existing `/query/stream` SSE endpoint, render
  tokens as they arrive
- Empty state: example questions, so a visitor never faces a blank box

### 2.3 Knowledge Graph Explorer (`app/[domain]/graph/page.tsx`)
- Full-bleed canvas, rail collapses to icon-only when this route is active
  (this section earns the most screen space - it's the most
  characteristic view of the product)
- Use `three.js` (already in your explored stack from the 3D portfolio
  work) with force-directed layout - nodes colored by entity type using a
  small consistent palette derived from `--signal` at varying opacity,
  not new hues per type. Fall back to a 2D force layout when WebGL is
  unavailable (react-force-graph-2d is acceptable for the core pass)
- Click a node → side panel slides in with its content + direct edges
- Search bar overlay (top-left) to jump to a node by name
- Reads `?node=<id>` from the URL: when present, center and highlight
  that node (this is how source chips deep-link into the graph)

### 2.4 Revision Dashboard (`app/exam-prep/revision/page.tsx`)
- **Not a card grid.** Lead with one large ring/radial showing overall
  mastery % across all subjects (the "big number" hero for this page,
  since it's actually the most characteristic content here)
- Below it, a sorted list (weakest first) - each row: topic name, a
  horizontal mastery bar (`--attention` fill for <50%, `--growth` for
  >80%, blend between), last reviewed date, times queried, and a
  "Query this topic" button that deep-links to `/exam-prep/query?topic=X`
- No red anywhere, even for 0% mastery - lowest end of the bar is still
  `--attention` amber, not alarm red

### 2.5 Roadmap (`app/exam-prep/roadmap/page.tsx`)
- Horizontal timeline from today to exam date, each day a vertical
  segment, height of colored blocks within each day proportional to
  hours allocated per subject that day
- Hover a block → tooltip with topic name, priority score, mastery %
- A "Regenerate" button at top-right, calls the roadmap recompute
  endpoint after new quiz/contest results are logged
- This page is explicitly sequential (a real timeline), so it's the one
  place numbered/dated markers are justified - everywhere else, avoid them

### 2.6 Document Library (`app/[domain]/library/page.tsx`)
- Simple list view: filename, ingested date, chunk count, entity count
- Upload dropzone at top - drag a file in, it posts to the ingestion
  endpoint with the current `domain_id`
- For `second-brain`: also show a "Last synced from vault" timestamp and
  a manual "Re-sync now" button, since that domain's source is external
  (your Obsidian vault), not directly uploaded here

---

## 3. State & Data Fetching

- No global state library needed - this app is small. Use React Server
  Components for initial data (graph snapshot, mastery scores) and a thin
  client wrapper only where interactivity is required (query streaming,
  graph click handlers).
- The URL is the source of truth for the active domain. The rail's toggle
  navigates; nothing stores the domain in app state.
- One shared `lib/api.ts` with typed functions per FastAPI endpoint,
  all accepting `domainId` as the first argument:
  ```ts
  export async function query(domainId: string, question: string) { ... }
  export async function getGraph(domainId: string) { ... }
  export async function getMastery(domainId: string) { ... }
  export async function getRoadmap(domainId: string) { ... }
  ```

---

## 4. Motion Rules

- The signal-pulse in Query Console is the **only** non-user-triggered
  animation in the app
- Everything else animates only in direct response to input: panel
  open/close, hover states, the mastery ring filling on first load of
  Revision Dashboard (one-time, not repeating)
- Animate only `transform` and `opacity`. Never `top`, `left`, `width`,
  `height`. No `window.scroll` listeners; no rAF loops touching state.
- Respect `prefers-reduced-motion` - signal-pulse becomes an instant
  highlight instead of a traveling line when set, and all entrances drop
  their translate and keep only a fast opacity crossfade
- Respect `prefers-reduced-transparency` - glass panels fall back to
  `--surface-solid` without blur

---

## 5. Icons & Emoji Policy

- Use one icon library, `@phosphor-icons/react`, for every glyph. Never
  hand-roll SVG icon paths, never use emoji as UI symbols.
- Emoji are banned in interface copy. Plain text or an icon carries the
  meaning instead.

---

## 6. Build Order

```
1. Scaffold Next.js app, Rail + layout shell, domain routing   → Checkpoint: switching domain changes URL, rail highlights correctly
2. lib/api.ts with typed fetch functions against existing FastAPI  → Checkpoint: one endpoint returns real data in browser console
3. Query Console (no signal-pulse yet, just working chat + streaming) → Checkpoint: real query round-trip works end to end
4. Graph Explorer (force layout, click-to-inspect, ?node deep-link)    → Checkpoint: real graph renders, nodes clickable
5. Wire signal-pulse animation between Query Console and Graph → Checkpoint: answering a query visibly traces to source nodes
6. Revision Dashboard (exam-prep only)                         → Checkpoint: real mastery data renders correctly sorted
7. Roadmap (exam-prep only)                                    → Checkpoint: timeline reflects real syllabus + mastery data
8. Document Library + upload flow                              → Checkpoint: uploading a file shows up in the list after ingest
9. Pass: reduced-motion, keyboard focus states, mobile breakpoint check
```

Do not skip the checkpoint after each step. Get one domain (exam-prep,
since it has the richest UI - revision + roadmap) fully working before
polishing the second-brain-specific views.