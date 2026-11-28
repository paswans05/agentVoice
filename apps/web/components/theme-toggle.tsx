"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle color theme"
      className="clay-btn inline-flex h-9 w-9 items-center justify-center rounded-xl bg-card text-foreground"
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {mounted ? (
        isDark ? <Sun className="h-4 w-4 text-[#E5A64B]" /> : <Moon className="h-4 w-4 text-[#7467D8]" />
      ) : (
        <span className="h-4 w-4" />
      )}
    </button>
  );
}
