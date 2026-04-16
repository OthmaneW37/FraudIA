/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        background: "#020617", // Slate 950
        surface: "rgba(15, 23, 42, 0.6)", // Slate 900 semi-transparent
        primary: {
          DEFAULT: "#38bdf8", // Sky 400
          glow: "rgba(56, 189, 248, 0.3)",
        },
        accent: {
          DEFAULT: "#818cf8", // Indigo 400
          glow: "rgba(129, 140, 248, 0.3)",
        },
        danger: "#f43f5e", // Rose 500
        success: "#10b981", // Emerald 500
      },
      animation: {
        'gradient-x': 'gradient-x 15s ease infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'gradient-x': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center',
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center',
          },
        },
      },
      backdropBlur: {
        'expert': '16px',
      }
    },
  },
  plugins: [],
}
