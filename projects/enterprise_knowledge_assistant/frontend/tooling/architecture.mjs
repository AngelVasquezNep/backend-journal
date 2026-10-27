/** ESLint rules enforcing resolved source ownership and documented public code. */
import path from 'node:path';
import { fileURLToPath, URL } from 'node:url';

const sourceRoot = fileURLToPath(new URL('../src/', import.meta.url));

/** Return the core layer of an absolute source path, or null for adapters/tooling. */
function coreLayer(filename) {
  const relative = path.relative(sourceRoot, filename);
  return /^(domain|application)(?:[/\\]|$)/u.exec(relative)?.[1] ?? null;
}

/** Check every supported literal import form against one resolved-target policy. */
function sourceImports(context) {
  const filename = context.filename;
  const layer = coreLayer(filename);
  /** Report relative source references, source escapes, and core dependency violations. */
  function check(node) {
    if (!node || typeof node.value !== 'string') return;
    const specifier = node.value;
    const relative = specifier.startsWith('.');
    const alias = specifier.startsWith('@/');
    const target = alias ? path.resolve(sourceRoot, specifier.slice(2))
      : relative ? path.resolve(path.dirname(filename), specifier) : null;
    const inSource = target !== null && !path.relative(sourceRoot, target).startsWith('..');
    if (relative && inSource) context.report({ node, messageId: 'alias' });
    if (alias && !inSource) context.report({ node, messageId: 'escape' });
    if (!layer) return;
    const targetLayer = target ? coreLayer(target) : null;
    if (targetLayer === 'domain' || (layer === 'application' && targetLayer === 'application')) return;
    context.report({ node, messageId: 'boundary' });
  }
  return {
    ImportDeclaration: (node) => check(node.source),
    ExportNamedDeclaration: (node) => check(node.source),
    ExportAllDeclaration: (node) => check(node.source),
    ImportExpression: (node) => check(node.source),
    TSImportType: (node) => check(node.argument),
  };
}

/** Require module and named callable documentation without treating callbacks as APIs. */
function documentation(context) {
  const source = context.sourceCode;
  /** Accept a standard doc comment attached to a declaration or its export wrapper. */
  function check(node) {
    const parent = node.parent?.type === 'ExportNamedDeclaration' ? node.parent : node;
    const comments = source.getCommentsBefore(parent);
    if (!comments.some((comment) => comment.type === 'Block' && comment.value.startsWith('*'))) {
      context.report({ node, messageId: 'required' });
    }
  }
  return {
    Program(node) {
      const first = source.getAllComments()[0];
      if (!first || first.type !== 'Block' || !first.value.startsWith('*')) {
        context.report({ node, messageId: 'required' });
      }
    },
    FunctionDeclaration: check,
    ClassDeclaration: check,
    MethodDefinition: check,
    VariableDeclaration(node) {
      if (node.declarations.some((decl) => ['ArrowFunctionExpression', 'FunctionExpression'].includes(decl.init?.type))) check(node);
    },
  };
}

export default {
  rules: {
    'source-imports': {
      meta: { type: 'problem', schema: [], messages: {
        alias: 'Use @/ for every import targeting frontend/src.',
        boundary: 'Domain/application imports must point inward to framework-free core modules.',
        escape: 'The @/ alias must resolve inside frontend/src.',
      } },
      create: sourceImports,
    },
    documentation: {
      meta: { type: 'problem', schema: [], messages: { required: 'Document the purpose, contract and applicable effects with a doc comment.' } },
      create: documentation,
    },
  },
};
