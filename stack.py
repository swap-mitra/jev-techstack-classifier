"""Rank software stack options for a business requirement using TypeSafe Jev.

Usage: python stack.py "requirements text"   (or pipe text on stdin)
       python stack.py --demo                (live self-check)
Needs TYPESAFE_API_KEY in the environment.
"""

import os
import sys
from pathlib import Path

from typesafe_sdk import Choice, Noul, TypeSafeClient

# ponytail: minimal KEY=value .env reader (no quotes/export syntax); use python-dotenv if .env grows
_env = Path(__file__).with_name(".env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LAYERS = {
    "frontend": {
        "react": "React / Next.js SPA or SSR web app",
        "vue": "Vue / Nuxt web app",
        "angular": "Angular enterprise web app",
        "svelte": "Svelte / SvelteKit lightweight web app",
        "server_rendered": "Server-rendered HTML templates (Django, Rails, Laravel views)",
        "none": "No web frontend needed (API-only, CLI, batch job, or mobile-only)",
    },
    "backend": {
        "node": "Node.js / TypeScript (Express, NestJS), good for real-time and JS teams",
        "python": "Python (Django, FastAPI), good for data, ML, and quick CRUD",
        "java": "Java / Kotlin (Spring Boot), large enterprise, regulated systems",
        "dotnet": "C# / .NET, Microsoft-centric enterprise",
        "go": "Go, high-concurrency services and infrastructure",
        "ruby": "Ruby on Rails, fast MVP CRUD apps",
        "php": "PHP (Laravel), content sites and cheap hosting",
        "baas": "Backend-as-a-service (Firebase, Supabase), minimal custom server",
    },
    "database": {
        "postgres": "PostgreSQL, relational data with integrity and reporting",
        "mysql": "MySQL / MariaDB, relational, common web apps",
        "mongodb": "MongoDB, flexible document data",
        "dynamodb": "DynamoDB / Cassandra, massive-scale key-value workloads",
        "redis": "Redis as primary store, ephemeral or very low-latency data",
        "timeseries": "Time-series DB (TimescaleDB, InfluxDB), metrics, IoT, sensor data",
        "sqlite": "SQLite, embedded, single-user or offline apps",
        "warehouse": "Data warehouse (BigQuery, Snowflake), analytics over large datasets",
    },
    "hosting": {
        "aws": "AWS, broad services, enterprise scale",
        "azure": "Azure, Microsoft ecosystem and enterprise compliance",
        "gcp": "Google Cloud, data and ML workloads",
        "paas": "PaaS (Vercel, Heroku, Render), small teams wanting zero ops",
        "on_prem": "On-premises / private data center, strict data residency or air-gapped",
    },
    "mobile": {
        "none": "No mobile app needed",
        "react_native": "React Native cross-platform app",
        "flutter": "Flutter cross-platform app",
        "native": "Native Swift (iOS) and Kotlin (Android) apps",
        "pwa": "Progressive web app instead of store apps",
    },
}

LOW_CONFIDENCE = 0.3  # docs' example threshold, not validated on this domain

# Jev can't write questions, so clarifications are canned: a Noul checks whether the
# requirements already cover the topic, and the UI asks only about uncovered ones.
CLARIFY = {
    "platform": {
        "check": "Do the requirements say which platforms the software must run on (web browser, iOS, Android, desktop, or backend/API only)?",
        "ask": "Where will people use it?",
        "options": ["Web browser", "iOS and Android apps", "Web and mobile", "Desktop", "API only, no UI"],
    },
    "scale": {
        "check": "Do the requirements indicate the expected number of users or traffic volume?",
        "ask": "How many users?",
        "options": ["Under 100 internal users", "Thousands of users", "Millions of users"],
    },
    "data": {
        "check": "Do the requirements describe what kind of data the software stores (e.g. transactional records, documents, metrics over time, analytics)?",
        "ask": "What data does it mainly store?",
        "options": ["Structured business records", "Flexible documents", "Time-series or sensor data", "Large analytics datasets"],
    },
}
CLARIFY_THRESHOLD = 0.5  # ask when "already covered" is less likely than not


def recommend(requirements: str) -> dict:
    """Rank every layer's options and list clarifying questions the text leaves open."""
    questions = {
        layer: Choice(
            instructions=f"Given the business requirements in `requirements`, which {layer} technology is most suitable to build this software?",
            criteria=options,
        )
        for layer, options in LAYERS.items()
    }
    questions |= {f"clarify_{k}": Noul(instructions=c["check"] + " Consider `requirements`.") for k, c in CLARIFY.items()}
    with TypeSafeClient() as client:
        response = client.system_one(state={"requirements": requirements}, questions=questions)
    layers = {}
    for layer in LAYERS:
        answer = response.choices[layer]
        ranked = sorted(answer.probabilities.items(), key=lambda kv: kv[1], reverse=True)
        layers[layer] = (ranked, answer.confidence)
    clarify = [
        {"id": k, "ask": c["ask"], "options": c["options"]}
        for k, c in CLARIFY.items()
        if response.nouls[f"clarify_{k}"].noul < CLARIFY_THRESHOLD
    ]
    usage = response.usage
    return {"layers": layers, "clarify": clarify, "tokens_in": usage.input_tokens, "tokens_out": usage.output_tokens}


def show(result) -> None:
    for c in result["clarify"]:
        print(f"? {c['ask']}  ({' / '.join(c['options'])})")
    for layer, (ranked, confidence) in result["layers"].items():
        flag = "  (low confidence)" if confidence < LOW_CONFIDENCE else ""
        print(f"\n{layer.upper()}  confidence {confidence:.2f}{flag}")
        for i, (option, p) in enumerate(ranked, 1):
            print(f"  {i}. {option:<16} {p:6.1%}  {LAYERS[layer][option]}")


def demo() -> None:
    result = recommend("A real-time chat mobile app for iOS and Android with millions of users.")
    for layer, (ranked, _) in result["layers"].items():
        probs = [p for _, p in ranked]
        assert probs == sorted(probs, reverse=True), layer
        assert abs(sum(probs) - 1) < 0.01, layer
        assert {o for o, _ in ranked} == set(LAYERS[layer]), layer
    assert result["layers"]["mobile"][0][0][0] != "none", "mobile app requested but ranked 'none' first"
    show(result)
    print("\ndemo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--demo"]:
        demo()
        sys.exit()
    text = " ".join(sys.argv[1:]).strip() or sys.stdin.read().strip()
    if not text:
        sys.exit("error: provide business requirements as arguments or on stdin")
    show(recommend(text))
