// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";
import reactHooks from 'eslint-plugin-react-hooks';

import js from '@eslint/js'
import ts from 'typescript-eslint'
import importPlugin from 'eslint-plugin-import'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

export default [js.configs.recommended, ...ts.configs.recommended, {
  files: ['**/*.{ts,tsx}'],
  languageOptions: {
    parserOptions: {
      project: './tsconfig.json',
      tsconfigRootDir: __dirname,
    },
  },
  plugins: {
    import: importPlugin,
    'react-hooks': reactHooks,
  },
  settings: {
    'import/resolver': {
      typescript: {
        project: './tsconfig.json',
      },
    },
  },
  rules: {
    'import/no-useless-path-segments': 'error',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'error',
    'no-restricted-imports': ['error', {
      patterns: [
        {
          group: [
            '^@/components/ui$',
            '^@/components/layout$',
            '^@/components/shared$',
            '^@/features/settings$',
            '^@/features/alerts$',
            '^@/features/configs$',
            '^@/api$',
            '^@/api/hooks$',
            '^@/types$',
            '^@/contexts$',
            '^@/pages$',
            '^@/services/api$',
          ],
          message: 'Avoid importing from barrel file directories. Import from a specific file instead.',
        },
        {
          group: [
            '/index$',
            '/index\\.ts$',
            '/index\\.tsx$',
          ],
          message: 'Avoid importing index barrel files directly.',
        },
      ],
    }],
  },
}, ...storybook.configs["flat/recommended"]];
