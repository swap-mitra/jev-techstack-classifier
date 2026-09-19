# Jev tech stack classifier

Describe a project in plain English and [TypeSafe Jev](https://docs.typesafe.ai) ranks
technology options for each stack layer (frontend, backend, database, hosting, mobile)
by probability. It is a classifier, not a generator: it only ranks the options listed in
`LAYERS` in `stack.py`.

When the description leaves platform, scale, or data type unclear, the app offers
clarifying questions. Answering one appends it to the description and re-runs.

## Setup

```sh
pip install -r requirements.txt
echo TYPESAFE_API_KEY=your-key > .env   # get a key at https://console.typesafe.ai/
```

## Run

Web UI:

```sh
python app.py   # http://localhost:8000
```

Visitors can paste their own key into the **JEV API KEY** field. It is stored only in
their browser (untick "remember" to keep it for the session) and sent to this server
with each request, which falls back to the server's `TYPESAFE_API_KEY` when none is given.

## Deploy

```sh
HOST=0.0.0.0 PORT=8000 python app.py
```

- Leave `TYPESAFE_API_KEY` unset (and don't ship `.env`) on a public deployment,
  otherwise every visitor runs on your key.
- Serve it behind HTTPS, since visitors' keys travel in a request header.

CLI:

```sh
python stack.py "Internal HR leave tracker for 50 employees"
python stack.py --demo   # live self-check against the API
```

## Customise

- Add or change technologies: edit `LAYERS` in `stack.py`.
- Add clarifying questions: edit `CLARIFY` in `stack.py`.
