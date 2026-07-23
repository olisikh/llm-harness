---
name: sops-secret-safety
description: This skill should be used when inspecting, editing, recovering, or rotating any SOPS-managed secret file, especially `~/.config/sops/secrets.yaml` or sops-nix materialized secrets.
---

# SOPS Secret Safety

## Trigger

Load this skill before any action involving `sops`, `sops-nix`, `~/.config/sops/`, `~/.config/sops-nix/secrets`, an encrypted YAML/JSON secret source, or an age identity.

## Approval gate

Before any secret mutation—adding, changing, rotating, deleting, recovering, or re-encrypting a secret; changing an age identity; or changing what sops-nix materializes—send an approval request through the **current chat** that names the exact change and reason. Wait for explicit approval in a later user message. Do not infer approval from an older request or bundle the request with the mutation.

Read-only inspection may proceed without an approval request, while still keeping values out of output.

## Non-negotiable invariants

1. Never redirect stdout from `sops set` to a file. `sops set` mutates its input file in place and can emit no document on stdout; a redirect can replace the source with an empty file.
2. Never overwrite a local source with encrypted content received from another machine until `sops --decrypt` succeeds with the local intended age identity. Preserve such content as a separate, clearly named encrypted artifact if it must be retained.
3. Never print, log, hash, commit, or return plaintext secret values. Report only file paths, status, permissions, top-level key names, and counts.
4. Before every mutation, verify that the current source is non-empty and decryptable. If it is not, stop and perform recovery rather than modifying it.
5. Use a `0600` temporary plaintext file only when recovery requires it. Delete it in a shell `trap` on every exit path. Build and validate an encrypted candidate before atomically replacing the active source.

## Standard verification

Run `scripts/verify-sops-source` before and after every mutation. Treat any non-zero result as a hard stop.

## Safe single-key update

1. Validate the current source with `scripts/verify-sops-source`.
2. Make an encrypted backup with `cp -p SOURCE SOURCE.backup-YYYYMMDD-HHMMSS`; never use a plaintext backup.
3. Run `sops set SOURCE INDEX --value-file VALUE_FILE` with **no shell redirection**. Create `VALUE_FILE` at mode `0600`, remove it in a trap, and keep it out of logs.
4. Validate the edited source with `scripts/verify-sops-source`.
5. Restart or activate the relevant `sops-nix` unit only after the source validates; verify that the required materialized file is non-empty and mode `0400` without reading its value.

## Recovery from materialized sops-nix secrets

Use only when the encrypted source is absent/corrupt but the required files still exist under `~/.config/sops-nix/secrets`.

1. Inventory materialized file **names, sizes, and modes** without reading values to output.
2. Build a temporary structured plaintext document from an explicit, reviewed key-to-file map. Include only secrets that are actually materialized; do not invent or silently substitute missing keys.
3. Encrypt to a candidate file using the active local age recipient.
4. Validate the candidate with `scripts/verify-sops-source CANDIDATE`.
5. Atomically rename the verified candidate into place, then delete the temporary plaintext file and confirm the sops-nix unit materializes all required files.
6. Explicitly report any keys that could not be recovered from materialized files.

## Functional evaluation

Before claiming success, require all of the following:

- `scripts/verify-sops-source` succeeds for the active source.
- The active source is non-empty and has mode `0600`.
- The selected `sops-nix` materialized secret files exist, are non-empty, and have mode `0400`.
- No terminal output or final response contains plaintext values.
- A cross-machine encrypted source is rejected unless its recipient matches a locally available age identity and decryption succeeds.
