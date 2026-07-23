/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0A2342",
          light: "#132A4C",
          50: "#E8EDF4",
        },
        gold: {
          DEFAULT: "#B8892B",
          light: "#D9B45C",
        },
        slate: {
          custom: "#5B6B82",
        },
        cream: "#F4F1EA",
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
      },
    },
  },
  plugins: [],
};
