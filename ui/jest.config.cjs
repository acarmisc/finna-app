module.exports = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { useESM: false }],
  },
  testRegex: '(/__tests__/.*|\\.(test|spec))\\.(ts|tsx|js)$',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/**/__snapshots__/**',
    '!src/main.tsx',
    '!src/query/**',
    '!src/config/**',
    '!src/env.d.ts',
  ],
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/src/main.tsx',
    '/src/test/',
    '/src/query/',
    '/src/services/apiClient.ts',
  ],
  coverageProvider: 'v8',
  rootDir: '.',
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  verbose: true,
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/services/apiClient$': '<rootDir>/src/__mocks__/services/apiClient.ts',
  },
}
