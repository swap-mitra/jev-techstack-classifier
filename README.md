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
cd worker && npm install && npx wrangler dev   # http://localhost:8787, page + API
```

Paste your key into the page.

## Deploy

Pages serves `docs/` from `main`. The `Deploy Worker` GitHub Action redeploys the Worker
when `worker/`, `stack_config.json` or `docs/` change (needs the `CLOUDFLARE_API_TOKEN`
repo secret). Manual deploy: `cd worker && npx wrangler deploy`. Allowed
browser origins are set by `ALLOWED_ORIGINS` in `worker/wrangler.toml`.

## Customise

- Technologies and clarifying questions: edit `stack_config.json`, then check with
  `cd worker && TYPESAFE_API_KEY=... npm run eval` against `wrangler dev`.
