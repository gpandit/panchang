"use client";

import { useEffect, useState } from "react";

/**
 * Resolves `prefers-reduced-motion`. Components must use this (or the
 * `motionDuration` helper below) instead of hardcoding transition durations,
 * so motion respects user/OS accessibility settings regardless of skin.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (e: MediaQueryListEvent): void => setReduced(e.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

/** Returns the named motion token duration, or "0ms" when motion is reduced. */
export function motionDuration(reduced: boolean, tokenVar: string): string {
  return reduced ? "0ms" : `var(${tokenVar})`;
}
