import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        border: "hsl(var(--border))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        clay: {
          success: "hsl(var(--clay-success))",
          warning: "hsl(var(--clay-warning))",
          danger: "hsl(var(--clay-danger))",
          info: "hsl(var(--clay-info))",
        },
      },
      borderRadius: {
        clay: "1.25rem",
        "clay-sm": "0.9rem",
        "clay-lg": "1.6rem",
      },
      boxShadow: {
        "clay-sm": "var(--clay-shadow-sm)",
        "clay-md": "var(--clay-shadow-md)",
        "clay-lg": "var(--clay-shadow-lg)",
        "clay-inset": "var(--clay-shadow-inset)",
        "clay-btn": "var(--clay-shadow-btn)",
      },
    },
  },
  plugins: [],
};

export default config;
