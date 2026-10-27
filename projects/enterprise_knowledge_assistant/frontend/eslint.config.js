/** Frontend lint configuration: strict TypeScript, documentation and inward dependencies. */
import js from '@eslint/js';
import ts from 'typescript-eslint';
import tsdoc from 'eslint-plugin-tsdoc';
import architecture from './tooling/architecture.mjs';

export default ts.config(
  { ignores: ['node_modules/**', 'dist/**', 'build/**', 'coverage/**', '*.min.js', '**/*.json', '**/*.yaml', 'playwright-report/**', 'test-results/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}', 'tests/**/*.{ts,tsx}'],
    plugins: { architecture, tsdoc },
    rules: { 'architecture/source-imports': 'error', 'architecture/documentation': 'error', 'tsdoc/syntax': 'error' },
  },
  {
    files: ['src/domain/**/*.ts', 'src/application/**/*.ts'],
    rules: { 'no-restricted-globals': ['error', 'window', 'document', 'fetch', 'globalThis', 'localStorage', 'sessionStorage', 'File', 'Blob', 'navigator', 'XMLHttpRequest', 'setTimeout', 'clearTimeout', 'crypto'] },
  },
  { files: ['tooling/**/*.mjs', '*config.*'], languageOptions: { globals: { process: 'readonly' } } },
);
