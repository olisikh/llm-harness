# Apple Notes Routing Policy

Use this policy when triaging Apple Notes for the configured Obsidian vault (`paths.obsidian_vault` in `~/.agents/config/skill-paths.json`).

## Vault Targets

| Target | Use for | Examples |
| --- | --- | --- |
| `10 Work/` | Professional notes, job search notes, interview prep, conference notes, work systems | job notes, interviews, AWS Summit, company research |
| `20 Learning/` | Courses, books, study notes, durable technical learning | DDIA, algorithms, LeetCode, Kubernetes, Nix |
| `20 Learning/Algorithms/` | Algorithm notes and coding interview patterns | LCA, graph traversal, dynamic programming |
| `20 Learning/Kubernetes/` | Kubernetes, Kuberstronaut, cluster operations | kubectl, CKA, operators |
| `20 Learning/Nix/` | Nix, NixOS, flakes, nix-darwin | flakes, derivations, package overrides |
| `30 Personal/` | Non-sensitive personal planning and durable life notes | personal projects, routines, non-sensitive plans |
| `30 Personal/Netherlands/` | Non-sensitive Netherlands life admin and knowledge | citizenship Q&A, housing research, Dutch language notes |
| `40 Reference/` | Reusable reference material, command snippets, tool notes, stable checklists | shell commands, app setup, plugin notes |
| `40 Reference/Apple Notes Import Review/` | Safe but unclassified notes needing manual placement | mixed notes, unclear context, low-confidence imports |

## Notes to Ignore

Ignore rather than import:

- Empty or near-empty notes.
- Duplicates already present in the vault.
- Default Apple Notes examples, untitled scratch notes, or recovered fragments.
- One-off shopping lists, packing lists, errands, restaurant ideas, temporary todos, and reminders.
- Verification codes, pasted SMS codes, or short login-related snippets.
- Notes whose only value is an attachment or scan that the script cannot safely export.
- Content that belongs in a password manager, finance tool, health record, government portal, or task manager.

## Sensitive Notes

Do not store these in the Obsidian vault as plain markdown:

- Passwords, passphrases, recovery codes, 2FA backup codes, API keys, access tokens, SSH/private keys, seed phrases, and crypto wallet details.
- Passport numbers, BSN, SSN, national IDs, residence permit numbers, driver's license numbers, scans of identity documents, and DigiD details.
- Bank account numbers, IBANs, credit card numbers, tax returns, payslips, salary details, invoices with personal identifiers, insurance policy numbers, and loan documents.
- Medical diagnoses, prescriptions, lab results, therapy notes, health insurance claims, and deeply private family details.
- Legal disputes, immigration applications with identifiers, contracts with signatures, confidential company data, or notes marked secret/private/confidential.

Reports may mention only title, folder path, and sensitivity category. Do not quote sensitive body text.

## Routing Heuristics

Prefer explicit Apple Notes folder context over keyword guesses. Use content keywords only when folder context is absent or generic.

- Route to `10 Work/` when title, folder, or body mentions jobs, interviews, company names, work planning, AWS events, professional goals, CV/resume content without private identifiers, or meeting notes safe to store.
- Route to `20 Learning/Algorithms/` for algorithm, LeetCode, data structure, coding problem, graph, tree, DP, or interview pattern notes.
- Route to `20 Learning/Kubernetes/` for Kubernetes, kubectl, Helm, clusters, CKA, Kuberstronaut, operators, deployments, services, or ingress.
- Route to `20 Learning/Nix/` for Nix, NixOS, nix-darwin, flakes, derivations, Home Manager, overlays, or package overrides.
- Route to `20 Learning/` for books, courses, technical notes, study plans, durable knowledge, or research that does not match a subfolder.
- Route to `30 Personal/Netherlands/` for Dutch citizenship, Netherlands housing research, language learning, gemeente process notes, and non-sensitive relocation/admin knowledge.
- Route to `30 Personal/` for durable non-sensitive personal notes that are not Netherlands-specific.
- Route to `40 Reference/` for reusable commands, setup notes, app/plugin configs, checklists, templates, and factual references.
- Route low-confidence safe notes to `40 Reference/Apple Notes Import Review/` with `review/apple-notes` tag.

## Import Shape

Use one markdown file per imported Apple Note. Keep filename human-readable and Obsidian-safe. Add frontmatter:

```yaml
---
source: apple-notes
apple_note_id: "..."
apple_account: "..."
apple_folder: "..."
created: "..."
modified: "..."
imported: "..."
tags:
  - imported/apple-notes
---
```

Add `review/apple-notes` tag for review-route notes.

## Obsidian Skill Hand-off

After import, use the installed Obsidian skills when cleanup goes beyond raw file writing:

- `obsidian:obsidian-markdown` or `obsidian-markdown`: normalize properties, tags, wikilinks, embeds, and callouts.
- `obsidian:obsidian-cli` or `obsidian-cli`: search the vault for duplicates, move notes, inspect backlinks, and validate Obsidian-visible state.
