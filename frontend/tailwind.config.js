/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Chivo", "sans-serif"],
        body: ["Manrope", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        pulse_glow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(59,130,246,0.2)" },
          "50%": { boxShadow: "0 0 40px rgba(59,130,246,0.4)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
        "scan-line": "scan-line 1.8s linear infinite",
        pulse_glow: "pulse_glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
