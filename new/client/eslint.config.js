import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import jsxA11y from 'eslint-plugin-jsx-a11y'
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
    plugins: { 'jsx-a11y': jsxA11y },
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
      // legacy accessibility findings are warnings; src/ui, src/app, src/filters are held to errors below
      ...Object.fromEntries(Object.keys(jsxA11y.flatConfigs.recommended.rules).map((r) => [r, 'warn'])),
      // ^motion$: framer-motion's <motion.div> is a JSX usage core ESLint does not track
      'no-unused-vars': ['error', { varsIgnorePattern: '^([A-Z_]|motion$)', argsIgnorePattern: '^[A-Z_]' }],
      // provider files export their hook next to the provider component
      'react-refresh/only-export-components': ['error', { allowConstantExport: true, allowExportNames: ['useToast', 'useAuth', 'useLayout', 'buttonVariants', 'useTabParam'] }],
    },
  },
  {
    // Accessibility problems anywhere are warnings (legacy code); the design-system folders must be clean.
    files: ['src/ui/**/*.{js,jsx}', 'src/app/**/*.{js,jsx}', 'src/filters/**/*.{js,jsx}'],
    rules: {
      'jsx-a11y/click-events-have-key-events': 'error',
      'jsx-a11y/no-static-element-interactions': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
      'no-restricted-syntax': ['error', { selector: "JSXAttribute[name.name='style']", message: 'Use utility classes; inline style is only for dynamic CSS variables.' }],
    },
  },
  {
    // Node-side files: build config, Playwright setup and specs
    files: ['vite.config.js', 'generate_storage_state.js', 'e2e/**/*.js', 'scripts/probe/**/*.js', 'playwright.config.js'],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
])
