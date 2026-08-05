# ValenciaGuard — AGENTS.md

Property management for Valencia rentals. FastAPI app (`app/`, entry
`app/main.py`), listens on `0.0.0.0:8473` and serves at the root path
(`root_path` in `app/config.py` is empty).

- Intranet: http://192.168.0.9:8473/ (home nginx `/valenciaguard` is only
  a redirect to that address)
- Public: https://valenciaguard.duckdns.org/ — Caddy on Frankfurt
  (8.211.26.86) → frps → frpc on machine 103 → 192.168.0.9:8473

## LLM usage (user requirement)

When a task needs an LLM, **prefer the local Kimi Code CLI first** — no API
key, uses the Kimi subscription login:

```bash
kimi -p "<prompt>"   # non-interactive, prints the response
```

- There is no `--output-schema` flag; ask for strict JSON in the prompt and
  extract the first `{...}` block from stdout (the CLI prints commentary
  around it).
- Fall back to `codex exec --skip-git-repo-check --sandbox read-only -o
  out.json "<prompt>"` (logged-in ChatGPT account) if kimi fails.
- **Do not rely on the Moonshot API** — that account is suspended for
  insufficient balance.
- Note: the app's own `app/services/ai_service.py` talks HTTP to
  `KIMI_BASE_URL`; on this machine `.env` points it at a local Codex shim
  (`http://127.0.0.1:8799`, see `~/.kimi-code/codex-shim.py`) backed by the
  ChatGPT subscription, so the app's AI features work. New agent-written LLM
  code should still use the `kimi -p` → `codex exec` chain above.
- Working kimi→codex fallback implementation to copy from:
  `~/Projects/nextERP/server.py`, function `_llm_parse`.
