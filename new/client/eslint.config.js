import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      // ^motion$: framer-motion's <motion.div> is a JSX usage core ESLint does not track
      'no-unused-vars': ['error', { varsIgnorePattern: '^([A-Z_]|motion$)' }],
      // provider files export their hook next to the provider component
      'react-refresh/only-export-components': ['error', { allowConstantExport: true, allowExportNames: ['useToast', 'useAuth', 'useLayout'] }],
    },
  },
  {
    // Node-side files: build config, Playwright setup and specs
    files: ['vite.config.js', 'generate_storage_state.js', 'e2e/**/*.js', 'playwright.config.js'],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
])
