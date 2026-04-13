# ThumbCraft

Production-grade YouTube thumbnail generator CLI + local web studio. Powered by Gemini 3 Pro Image with reverse-engineered 1of10 intelligence (outlier scoring, reference injection, thumbnail-title pairing).

## Quickstart

```bash
# 1. Install
python -m venv .venv
.venv\Scripts\activate    # Windows bash: source .venv/Scripts/activate
pip install -e .

# 2. Configure
cp config.yml.example config.yml
# Edit config.yml and add your GCP project id + YouTube API key

# 3. Authenticate Vertex AI
gcloud auth application-default login

# 4. Generate
thumbcraft generate "How a 19-Year-Old Built a $2M AI Empire" --channel ai-hustler

# 5. (Phase 6+) Launch web UI
thumbcraft studio
```

## Status

- [x] Phase 1 — Foundation: scaffold, Gemini client, basic CLI
- [ ] Phase 2 — Reference scraper + outlier engine
- [ ] Phase 3 — Agents
- [ ] Phase 4 — Intelligence (scene gen, prompt engine)
- [ ] Phase 5 — Compositing
- [ ] Phase 6 — Profiles, web UI
- [ ] Phase 7 — Hardening

See [THUMBCRAFT_MASTERPLAN.md](THUMBCRAFT_MASTERPLAN.md) for the full plan.
