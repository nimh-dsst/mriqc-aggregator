# Repository Notes

## Commit Gating

- Run `pixi run validate` before committing when a change touches both Python and frontend code.
- At minimum, commits must satisfy the configured local hooks:
  - `pre-commit`: Python lint/format checks plus frontend lint
  - `pre-push`: Python test suite
- Install the hooks with `pixi run install-hooks`.

## Deployment Safety

- Preserve `/data` on the production host.
- Do not use `tofu destroy` when the production PostgreSQL contents matter.
