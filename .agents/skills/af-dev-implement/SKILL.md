---
name: af-dev-implement
description: Axiom Forge system software development only. Implement a piece of work based on a spec or set of tickets.
disable-model-invocation: true
---

> Project scope: use only for Axiom Forge system software development in this repository. Read [engineering workflow](../../../development/records/skills/README.md) before acting. This skill is not a worldbuilding research role, Evidence source, tool grant, approval or permission to publish.


Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Call the Skill tool with "af-dev-tdd" where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, call the Skill tool with "af-dev-code-review" to review the work.

Commit your work to the current branch.
