/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
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
          navy: '#01204E',      // Dark Navy Blue (Main Button / Light heading)
          teal: '#028391',      // Teal Blue (Button Accent / Light body)
          cream: '#F6DCAC',     // Cream Sand (Light Card / Dark text)
          peach: '#FAA968',     // Soft Orange (Light Canvas)
          orange: '#F85525',    // Vibrant Orange (Main CTA in dark mode, highlight in light)
          darkCanvas: '#06101E',// Inky Abyss Canvas
          darkCard: '#0C1D36',  // Elevated Midnight Card Surface
          darkNav: '#112746',   // Dark Navbar Capsule
          darkPill: '#132B4F',  // Elevated Pill Surface
          lightTeal: '#8FE3EC', // Luminous readable teal for dark mode text
          creamText: '#F8EBD5', // Warm Cream White headings
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
          darkCanvas: '#06101E',
          darkCard: '#0C1D36',
          lightTeal: '#8FE3EC',
          creamText: '#F8EBD5',
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
