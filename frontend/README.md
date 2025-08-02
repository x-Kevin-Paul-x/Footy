# Footy Frontend

A modern football management dashboard built with React, TypeScript, and Vite. This app provides interactive analytics, team management, player profiles, transfer market insights, youth academy tracking, and more.

## Main Features

- League overview and statistics
- Team and player profiles
- Manager and coach details
- Match and season reports
- Transfer market analysis
- Youth academy management
- Interactive dashboard and analytics

## Prerequisites

- [Node.js](https://nodejs.org/) (v16 or newer recommended)
- [npm](https://www.npmjs.com/) (comes with Node.js)

## Installation

1. Open a terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

## Running the App

Start the development server:
```bash
npm run dev
```
Then open [http://localhost:5173/](http://localhost:5173/) in your browser.

## Troubleshooting

- **Port conflicts:** If port 5173 is in use, Vite will prompt you to use another port or you can specify one:
  ```bash
  npm run dev -- --port=5180
  ```
- **Node/npm issues:** Ensure Node.js and npm are installed and up to date.
- **Dependency errors:** Delete `node_modules` and `package-lock.json`, then run `npm install` again.

## Additional Info

This project uses Vite for fast development and hot module replacement. ESLint and TypeScript are configured for code quality and type safety. See below for expanding ESLint configuration and plugins.

---

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config({
  extends: [
    ...tseslint.configs.recommendedTypeChecked,
    ...tseslint.configs.strictTypeChecked,
    ...tseslint.configs.stylisticTypeChecked,
  ],
  languageOptions: {
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config({
  plugins: {
    'react-x': reactX,
    'react-dom': reactDom,
  },
  rules: {
    ...reactX.configs['recommended-typescript'].rules,
    ...reactDom.configs.recommended.rules,
  },
})
