# CampusHub 1.0 — Fix Instructions

Five gaps were found in the current repo against the build spec. This article summarizes each fix and the recommended execution order.

## Fix 1 — Real Responsive Layout

The current `.app-frame` uses a fixed 440px width with no `@media` queries. Real mobile/tablet browsers get the wrong layout.

**Action:** Replace fixed width with fluid sizing and add breakpoints for mobile (default), tablet (640px+), and desktop (1024px+). The "Mobile Frame" toggle becomes a design preview tool, not the only adaptation mechanism.

## Fix 2 — PWA Manifest + Service Worker

No `manifest.json` or service worker exists. The app can't be installed on home screens.

**Action:** Create `manifest.json` with app metadata, add two icon files, create a cache-first service worker (`js/sw.js`), and register it in `index.html`.

## Fix 3 — Remove/Gate Account Switcher

The "Switch Role" button lets anyone jump into any account without a password, contradicting the spec's credential requirement.

**Option A (recommended):** Delete the switcher from the dev toolbar. Users must log in with email + password.
**Option B:** Gate behind `?dev=1` query param for development-only use.

## Fix 4 — Fix README

README claims accounts are "preloaded" but the code seeds zero accounts. Replace with accurate description of the live registration model.

## Fix 5 — Real-time Accept/Decline

`localStorage` means Accept/Decline only works within one browser. For true multi-device demo, migrate `registeredUsers`, `requests`, and `chats` to Supabase with Realtime subscriptions.

## Execution Order

1. **Mission A:** Fix 1 (responsive CSS) + Fix 2 (PWA) — pure frontend/config
2. **Mission B:** Fix 3 (account switcher) — small isolated change
3. **Mission C:** Fix 4 (README) — doc fix
4. **Mission D:** Fix 5 (Supabase) — only if multi-device needed

## Key Takeaways

- Responsive layout must use real `@media` breakpoints, not manual toggles
- PWA support requires manifest.json + service worker + icons
- Account security requires real authentication, not one-click switching
- README must match actual code behavior
- [[jarvis]] shows similar patterns of stub-vs-reality gaps
