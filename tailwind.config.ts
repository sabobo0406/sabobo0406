import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a1a",
        paper: "#faf9f6",
        accent: "#e07a5f",
        sub: "#6b7280",
      },
    },
  },
  plugins: [],
};

export default config;
