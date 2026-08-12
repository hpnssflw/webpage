# polozov

Artem Polozov's personal site, plus a planned research agent that feeds
his own writing.

## Structure

- `index.html`, `styles.css`, `assets/`, `photo.jpg` — homepage (hero,
  RESEARCHER topics, LAB feed preview)
- `lab/` — the "LAB" blog: `lab/index.html` is the full listing, plus one
  post so far
- `researcher/` — `index.html` is a topics hub page; `agent.html` is the
  research agent's public-facing plan
- `docs/superpowers/` — design specs and implementation plans for each
  site feature, in build order
- `docs/agent-plan.md` — the technical (implementation-facing) plan for
  the research agent
- `agent/` — the agent's implementation. **Doesn't exist yet** — see
  `PROGRESS.md`.

## Running locally

```
python -m http.server 5678 --bind 127.0.0.1
```

then open http://127.0.0.1:5678/. No build step.

## Status

Site: built. Research agent: planned, not implemented — see
`PROGRESS.md` for what's next.
