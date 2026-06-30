# OpenClaw doctor: non-interactive repair

Use this when maintaining a source-installed OpenClaw and you want safe repairs without an interactive prompt.

## Commands

```bash
openclaw doctor --repair --non-interactive
openclaw doctor --lint --json
openclaw status
openclaw models status
openclaw models auth list
```

## Observed behavior in this build

- `--non-interactive` is accepted by `openclaw doctor` and pairs well with `--repair`.
- `--fix` is documented as an alias for `--repair`.
- `--lint` is read-only; add `--json` when you want machine-readable findings.
- `openclaw status` is the quickest verification step after repairs.
- For auth inspection in this build, use `openclaw models status` and `openclaw models auth list`.

## Practical workflow

1. Inspect help: `openclaw doctor --help`
2. Apply safe repairs: `openclaw doctor --repair --non-interactive`
3. Verify service health: `openclaw status`
4. If needed, inspect model/auth state: `openclaw models status` and `openclaw models auth list`

## Notes

- Keep any credential/SecretRef remediation separate from the doctor run; doctor will not overwrite a managed secret with plaintext.
- Use `--deep` only when you need additional system-service probing.
