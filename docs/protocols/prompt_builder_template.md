# Prompt Builder Engine

Build prompts in strict order:
1. System prompt with role + strict rules.
2. Persona section.
3. Architecture/project context.
4. Current task.
5. Path-switched documentation references.
6. Current code.
7. Error feedback from QA/sandbox.

No conversation history is used; context is injected every turn.
