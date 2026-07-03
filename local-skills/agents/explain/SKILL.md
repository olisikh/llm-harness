---
name: explain
description: Explain code, a concept, or a system clearly. Use when the user asks "what does this do", "explain X", "how does Y work", or "I don't understand Z". Adapts depth to what the user is asking about.
argument-hint: [code, file, concept, or question]
---

## Instructions

Explain: $ARGUMENTS

If $ARGUMENTS is empty, explain the currently open file or the last piece of code discussed.

Rules for a good explanation:
1. Start with one sentence: what it does and why it exists.
2. Then explain how — the key mechanism, pattern, or flow. Use concrete examples where helpful.
3. Call out anything surprising, non-obvious, or likely to trip someone up.
4. If there are tradeoffs or alternatives, mention them briefly.
5. Match depth to the question — a "what does this line do" needs 2 sentences, not a full essay.

Do not repeat back what the code literally says — the reader can see the code. Explain the intent and the mental model needed to understand it.

## Special case: capability / configuration questions

When the user is asking what a product, repo, agent, bot, or integration *currently supports* (for example: "can Hermes do X via config?"), treat it as a shallow capability check rather than a build/implementation task.

1. Respect research-only scope. If the user says they only want research, do not drift into setup steps, edits, or "here's how I'd implement it" unless they explicitly ask.
2. Prefer a narrow pass over docs + source-of-truth references, not a sprawling investigation.
3. Separate these outcomes clearly:
   - **Supported now via config**
   - **Works, but not visible/discoverable in the surface the user cares about**
   - **Possible only via code/plugin changes**
   - **Not supported today**
4. If the user says code changes are not viable, treat any code/plugin path as a non-answer and say so plainly.
5. For operational capability questions, answer in the user's decision frame, not in implementation detail. A compact verdict like "config-only: no; skills: yes; code/plugin path: possible but out of scope" is better than a long architecture tour.
6. When persistence matters (restart, reboot, gateway restart, session reset), call it out explicitly instead of leaving the user to infer it.
