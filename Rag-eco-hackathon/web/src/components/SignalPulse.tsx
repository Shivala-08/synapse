'use client';

/**
 * The signal pulse: a single animated trace from the answer bubble's lower
 * left (where the graph sits) toward the source chips above it. It plays
 * once when the answer with sources mounts, then fades. Under
 * prefers-reduced-motion the CSS hides the path entirely and the source
 * chips flash instantly instead (see globals.css).
 */
export default function SignalPulse() {
  return (
    <svg
      className="signal-pulse running"
      viewBox="0 0 100 42"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M 2 38 C 30 38, 26 6, 72 4" />
    </svg>
  );
}