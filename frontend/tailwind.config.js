/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c1612",
        cream: "#f4efe6",
        paper: "#fffdf8",
        line: "#e5d9c8",
        amber: {
          DEFAULT: "#e0892d",
          dark: "#b86a14",
        },
        terra: "#c45c3e",
        sage: "#3e7a5a",
      },
      fontFamily: {
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 16px 40px rgba(28, 22, 18, 0.08)",
      },
    },
  },
  plugins: [],
};
