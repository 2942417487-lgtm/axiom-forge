---
name: af-dev-handoff
description: Axiom Forge system software development only. Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: What will the next session be used for?
disable-model-invocation: true
---

> Project scope: use only for Axiom Forge system software development in this repository. Read [engineering workflow](../../../development/records/skills/README.md) before acting. This skill is not a worldbuilding research role, Evidence source, tool grant, approval or permission to publish.


Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save a handoff section in the current task under `development/records/tasks/`, and update `development/records/CURRENT.md` to point to it. If a separate handoff file is needed, keep it beside that task; preserve existing records instead of overwriting them. Use the OS temporary directory only for disposable previews, never as the sole development memory.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
