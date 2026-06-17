import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        matte: {
          950: "#2a0138",
          900: "#4a0f63",
          850: "#6c1e83",
          800: "#8f31a2",
          700: "#b64bbf"
        },
        neon: {
          blue: "#7f6bff",
          soft: "#ffeaf5",
          pink: "#ffd6ea"
        }
      },
      boxShadow: {
        "neon-ring": "0 0 0 1px rgba(88, 33, 120, 0.72)",
        "neon-glow": "0 0 0 1px rgba(88, 33, 120, 0.68), 0 0 24px rgba(255, 214, 234, 0.4)",
        panel: "0 24px 48px rgba(40, 6, 56, 0.4)"
      },
      backgroundImage: {
        "matte-gradient":
          "radial-gradient(1250px circle at 8% -12%, rgba(255, 208, 232, 0.42), transparent 35%), radial-gradient(1100px circle at 100% 10%, rgba(198, 118, 255, 0.38), transparent 38%), linear-gradient(180deg, #3a0b5f 0%, #6a1f8e 52%, #c449a8 100%)"
      },
      fontFamily: {
        sans: ["Sora", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
