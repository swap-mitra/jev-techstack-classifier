# Jev tech stack classifier

**Live:** https://swap-mitra.github.io/jev-techstack-classifier/ (bring your own
[TypeSafe API key](https://console.typesafe.ai/))

Describe a project in plain English and [TypeSafe Jev](https://docs.typesafe.ai) ranks
technology options for each stack layer (frontend, backend, database, hosting, mobile)
by probability. It is a classifier, not a generator: it only ranks the options listed in
`stack_config.json`.

When the description leaves platform, scale, or data type unclear, the app offers
clarifying questions. Answering one appends it to the description and re-runs.

## How it's hosted

```
GitHub Pages (docs/index.html)  ──POST + X-TypeSafe-Key──▶  Cloudflare Worker (worker/)  ──▶  api.typesafe.ai
```

The TypeSafe API rejects browser requests from other sites, so the static page can't
call it directly. The Worker forwards each request using the visitor's own key, which the
page keeps in their browser only if "remember" is ticked. The Worker has no key of its
own and stores nothing.

## Run locally

```sh
pip install -r requirements.txt
echo TYPESAFE_API_KEY=your-key > .env
python app.py   # http://localhost:8000, serves docs/index.html plus the same API
```

Locally the server falls back to `TYPESAFE_API_KEY` when the page sends no key.

CLI:

```sh
python stack.py "Internal HR leave tracker for 50 employees"
python stack.py --demo   # live self-check against the API
```

## Deploy

Pages serves `docs/` from `main`. To deploy the Worker:

```sh
cd worker
npm install
npx wrangler login
npx wrangler deploy
```

Put the printed `*.workers.dev` URL into `WORKER_URL` in `docs/index.html`. Allowed
browser origins are set by `ALLOWED_ORIGINS` in `worker/wrangler.toml`.

## Customise

- Technologies and clarifying questions: edit `stack_config.json` (used by both the
  Python app and the Worker).
