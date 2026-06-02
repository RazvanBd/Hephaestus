# Internal Service: LLM Gateway & XML Parser

## LLM Gateway requirements
- Async I/O (`aiohttp`), memoryless prompt->response behavior.
- Retry on timeout/empty response (up to 3 with backoff).

## XML parser requirements
- Strip markdown fences before parsing.
- Extract `<file>`, `<doc_update>`, `<execute>`, `<transition_to>`.
- If no valid tags: request reformatted response, do not crash.
