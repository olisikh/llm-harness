---
name: test-gen
description: Generate tests for a function, file, or feature. Use when the user asks to "write tests", "add coverage", "test this function", or "generate unit tests". Produces tests that match the existing test style.
argument-hint: [file-or-function]
---

## Instructions

Generate tests for: $ARGUMENTS

1. Read the target code (file or function named in $ARGUMENTS, or the file currently being discussed).
2. Find existing tests to understand the framework, style, and conventions used (Jest, pytest, JUnit, etc.).
3. Write tests that cover:
   - Happy path (expected inputs and outputs)
   - Edge cases (empty, null, zero, boundary values)
   - Error/exception paths
   - Any logic branches visible in the code
4. Match the existing test file structure exactly — same imports, describe/test blocks, assertion style.
5. Place tests in the appropriate file or create a new one following the project's naming convention.
6. Do not test implementation details; test observable behavior.

Keep tests concise. One assertion per test is preferred unless setup cost is high.
