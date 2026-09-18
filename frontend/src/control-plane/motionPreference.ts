import { useEffect, useState } from "react";

export function useMotionPreference() {
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [paused, setPaused] = useState(() => {
    try {
      return localStorage.getItem("cortex-motion") === "paused";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.motion = reduced || paused ? "off" : "on";
    try {
      localStorage.setItem("cortex-motion", paused ? "paused" : "on");
    } catch {
      /* Storage is optional. */
    }
  }, [paused, reduced]);
  return {
    enabled: !reduced && !paused,
    reduced,
    toggle: () => setPaused((value) => !value),
  };
}
