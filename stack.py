"""Rank software stack options for a business requirement using TypeSafe Jev.

Usage: python stack.py "requirements text"   (or pipe text on stdin)
       python stack.py --demo                (live self-check)
Needs TYPESAFE_API_KEY in the environment.
"""

import json
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

# Options and clarifying questions live in JSON so the Cloudflare Worker uses the same list.
_config = json.loads(Path(__file__).with_name("stack_config.json").read_text(encoding="utf-8"))
LAYERS: dict[str, dict[str, str]] = _config["layers"]

LOW_CONFIDENCE = 0.3  # docs' example threshold, not validated on this domain

# Jev can't write questions, so clarifications are canned: a Noul checks whether the
# requirements already cover the topic, and the UI asks only about uncovered ones when the
# "covered" probability is below that entry's threshold. Thresholds were tuned on 15
# hand-labelled prompts (all separated cleanly); retune on real traffic.
CLARIFY: dict[str, dict] = _config["clarify"]


def recommend(requirements: str, api_key: str | None = None) -> dict:
    """Rank every layer's options and list clarifying questions the text leaves open.

    api_key overrides TYPESAFE_API_KEY from the environment.
    """
    questions = {
        layer: Choice(
            instructions=f"Given the business requirements in `requirements`, which {layer} technology is most suitable to build this software?",
            criteria=options,
        )
        for layer, options in LAYERS.items()
    }
    questions |= {f"clarify_{k}": Noul(instructions=c["check"] + " Consider `requirements`.") for k, c in CLARIFY.items()}
    with TypeSafeClient(api_key=api_key) as client:
        response = client.system_one(state={"requirements": requirements}, questions=questions)
    layers = {}
    for layer in LAYERS:
        answer = response.choices[layer]
        ranked = sorted(answer.probabilities.items(), key=lambda kv: kv[1], reverse=True)
        layers[layer] = (ranked, answer.confidence)
    clarify = [
        {"id": k, "ask": c["ask"], "options": c["options"]}
        for k, c in CLARIFY.items()
        if response.nouls[f"clarify_{k}"].noul < c["threshold"]
    ]
    usage = response.usage
    return {
        "layers": layers,
        "descriptions": LAYERS,
        "clarify": clarify,
        "model": response.model,
        "tokens_in": usage.input_tokens,
        "tokens_out": usage.output_tokens,
    }


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
