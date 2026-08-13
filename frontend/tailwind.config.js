/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Outfit', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        heading: ['Outfit', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      colors: {
        palette: {
          navy: '#01204E',      // Dark Navy Blue (Main Button)
          teal: '#028391',      // Teal Blue (Button Accent)
          cream: '#F6DCAC',     // Cream Orange (Background Base)
          peach: '#FAA968',     // Soft Orange (Card/Paper Background)
          orange: '#F85525',    // Vibrant Orange (Spotlight/Accent Background)
        },
        retro: {
          navy: '#01204E',
          deepNavy: '#01204E',
          red: '#F85525',
          orange: '#FAA968',
          peach: '#FAA968',
          cream: '#F6DCAC',
          sand: '#F6DCAC',
          teal: '#028391',
          darkTeal: '#01204E',
        },
        indigo: {
          500: '#01204E',
          600: '#028391',
          700: '#01204E',
        },
        navy: {
          800: '#01204E',
          900: '#01204E',
          950: '#01204E',
        },
      },
    },
  },
  plugins: [],
}
