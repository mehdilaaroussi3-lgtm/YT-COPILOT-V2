# YTcopilot — Repo Rules for Claude

## Text vs. Vision routing (HARD RULE)

All **text** LLM calls route through the local Claude CLI, via
`generators/claude_text.py`. This is the default engine; it is wired into
`generators/gemini_text.generate_text()` as a router, so every existing
import site (`from generators.gemini_text import generate_text`) already
goes through Claude with no changes.

The Gemini **text** path is kept behind `text.engine: "gemini"` in
`config.yml` as an escape hatch — do not use it for new code.

**Vision and image generation stay on the Gemini API.** Specifically:
- `core/channel_text_dna.build_text_dna` (thumbnail text DNA via Gemini Vision)
- `generators/gemini_client.py` (image generation)
- `scraper/thumbnail_analyzer.py` (vision describe)

Never call the Gemini API for plain text. Never call Claude for images.

## Naming

User-facing display name is **YTcopilot**. Model display labels use
**YTC 2.5** and **YTC 3.0** (these are display aliases — the underlying
API model IDs `gemini-2.5-pro` and `gemini-3-pro-image-preview` stay as-is
in code/config since they are what the Vertex API expects).

Invariants that must NOT be renamed (would break installs / existing data):
- CLI command name `thumbcraft` (`pyproject.toml` script entry)
- DB filename `data/thumbcraft.db`
- Python module / package / file names (e.g. `generators/gemini_text.py`,
  `generators/gemini_client.py`)

## Do-not-break list

- Don't bypass the router: always import `generate_text` from
  `generators.gemini_text` (the router) or `generators.claude_text`
  directly. Never call `_generate_text_gemini` for anything new.
- Don't touch temperatures in the text prompts on engine swap — Claude CLI
  ignores temperature, and prompts are model-agnostic.
- Don't rename model IDs in API calls. Only rename display strings.
