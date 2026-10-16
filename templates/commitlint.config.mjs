// Conventional Commits with the standard types only (CONTRIBUTING.md).
// Used by the commit-msg hook and by the PR title check in CI.
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'perf', 'refactor', 'test', 'docs', 'build', 'ci', 'chore', 'revert', 'style'],
    ],
    'header-max-length': [2, 'always', 72],
  },
};
