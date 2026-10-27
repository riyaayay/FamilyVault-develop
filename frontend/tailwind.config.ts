import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "character-purple": "#5F3DF7",
        "character-orange": "#FF6B4A",
        "character-yellow": "#F4D33A",
        "character-dark": "#1A1A1A",
        "panel-canvas": "#E8E8E8",
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      keyframes: {
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "20%": { transform: "translateX(-6px)" },
          "40%": { transform: "translateX(6px)" },
          "60%": { transform: "translateX(-4px)" },
          "80%": { transform: "translateX(4px)" },
        },
      },
      animation: {
        shake: "shake 400ms cubic-bezier(0.4,0,0.2,1)",
      },
    },
  },
  plugins: [],
};

export default config;
