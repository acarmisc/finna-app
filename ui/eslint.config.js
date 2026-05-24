import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import globals from 'globals'

/** @type {import('eslint').Linter.Config[]} */
export default [
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: true,
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
    },
    rules: {
      ...typescript.configs['eslint-recommended'].rules,
      ...typescript.configs['recommended'].rules,
      // Ban JSON.stringify in dependency arrays to prevent unnecessary refetches
      // caused by object key ordering or undefined value differences across runtimes
      'no-restricted-syntax': [
        'error',
        {
          selector: "CallExpression[callee.name='JSON.stringify']",
          message:
            'Avoid JSON.stringify() in hook dependency arrays. Use createParamsKey() or primitive deps instead.',
        },
      ],
    },
  },
]
