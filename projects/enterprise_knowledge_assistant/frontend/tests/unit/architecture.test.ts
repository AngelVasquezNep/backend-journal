/** Boundary regression cases: import syntax and aliases cannot bypass core ownership. */
// @vitest-environment node
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Linter } from 'eslint';
import ts from 'typescript-eslint';
import { describe, expect, it } from 'vitest';
// @ts-expect-error Local ESLint plugin is intentionally plain JavaScript.
import architecture from '../../tooling/architecture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));

/** Lint a source snippet at a simulated consumer path and return policy messages. */
function violations(code: string, consumer = 'src/adapters/inbound/react/example.ts') {
  const linter = new Linter();
  return linter.verify(code, [{
    files: ['**/*.ts'],
    languageOptions: { parser: ts.parser },
    plugins: { architecture },
    rules: { 'architecture/source-imports': 'error' },
  }], { filename: path.join(root, consumer) });
}

describe('source import convention', () => {
  it.each([
    'import "./peer";',
    'import type { Peer } from "./peer";',
    'export { peer } from "./peer";',
    'export * from "./peer";',
    'void import("./peer");',
  ])('rejects relative references: %s', (code) => {
    expect(violations(code).some((message) => message.messageId === 'alias')).toBe(true);
  });
  it('requires aliases for test consumers importing source', () => {
    expect(violations('import "../../src/domain/value";', 'tests/unit/example.ts')).toHaveLength(1);
  });
  it('permits alias imports, packages, and tooling helper references', () => {
    expect(violations('import "@/domain/value"; import "react";')).toHaveLength(0);
    expect(violations('import "./helper";', 'tests/unit/example.ts')).toHaveLength(0);
    expect(violations('import "@/domain/value";', 'src/application/example.ts')).toHaveLength(0);
  });
  it.each(['@/adapters/outbound/http/client', '@/application/usecase', 'react', '@/../tooling/escape'])('rejects domain boundary bypass: %s', (specifier) => {
    expect(violations(`import "${specifier}";`, 'src/domain/example.ts').length).toBeGreaterThan(0);
  });
});
