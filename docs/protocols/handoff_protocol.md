# Handoff Protocol (Agent Output Formatting)

Agents must communicate with XML tags only.

## Required tags
- `<file path="src/..." action="create|update">...</file>`
- `<doc_update path="docs/..." action="upsert|update|create">...</doc_update>`
- `<execute>...</execute>`
- `<transition_to>STATE</transition_to>`

Any text outside valid tags is ignored for execution and preserved in session logs.
