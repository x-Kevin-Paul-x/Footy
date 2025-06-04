/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
        heading: ['Montserrat', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        'primary-bg': '#1A1A1A',
        'secondary-bg': '#2A2A2A',
        'tertiary-bg': '#333333',
        'primary-text': '#E0E0E0',
        'secondary-text': '#999999',
        'accent-blue': '#007BFF',    // Example: Bootstrap Blue
        'accent-green': '#39FF14',   // Neon Green
        'accent-purple': '#8A2BE2',  // BlueViolet
        'accent-cyan': '#00FFFF',    // Aqua/Cyan
        // You can add more specific shades if needed, e.g., accent-blue-hover
      },
    },
  },
  plugins: [],
}
