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
