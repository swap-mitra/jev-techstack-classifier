/**
 * Cloudflare Worker backend for the GitHub Pages site. Browsers can't call the TypeSafe
 * API directly (it rejects cross-origin requests), so this forwards each request using
 * the visitor's own key from the X-TypeSafe-Key header. It never stores or logs the key.
 *
 * Mirrors recommend() in ../../stack.py and returns the same JSON shape.
 */
import config from "../../stack_config.json";

interface Env {
  ALLOWED_ORIGINS: string;
}

type ClarifyEntry = { check: string; ask: string; options: string[]; threshold: number };
type ChoiceAnswer = { type: "choice"; probabilities: Record<string, number>; confidence: number };
type NoulAnswer = { type: "noul"; noul: number };
type SystemOneResponse = {
  model: string;
  answers: Record<string, ChoiceAnswer | NoulAnswer>;
  usage: { input_tokens: number; output_tokens: number };
};

const LAYERS: Record<string, Record<string, string>> = config.layers;
const CLARIFY: Record<string, ClarifyEntry> = config.clarify;
const TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone";
const MAX_CHARS = 5000;
const MAX_KEY_CHARS = 512;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get("Origin") ?? "";
    const allowed = env.ALLOWED_ORIGINS.split(",").map((o) => o.trim());
    const cors: Record<string, string> = allowed.includes(origin)
      ? {
          "Access-Control-Allow-Origin": origin,
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-TypeSafe-Key",
          "Access-Control-Max-Age": "600",
          Vary: "Origin",
        }
      : { Vary: "Origin" };
    const json = (status: number, body: unknown) =>
      new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });

    const { pathname } = new URL(request.url);
    if (pathname !== "/api/recommend") return json(404, { error: "not found" });
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json(405, { error: "use POST" });

    let text: unknown;
    try {
      text = ((await request.json()) as { requirements?: unknown }).requirements;
    } catch {
      return json(400, { error: 'body must be JSON {"requirements": "..."}' });
    }
    if (typeof text !== "string" || !text.trim() || text.trim().length > MAX_CHARS) {
      return json(400, { error: `requirements must be 1-${MAX_CHARS} characters` });
    }
    const apiKey = request.headers.get("X-TypeSafe-Key")?.trim();
    if (!apiKey) return json(401, { error: "Enter your TypeSafe API key to run the classifier" });
    if (apiKey.length > MAX_KEY_CHARS) return json(400, { error: "API key is too long" });

    const questions: Record<string, object> = {};
    for (const [layer, options] of Object.entries(LAYERS)) {
      questions[layer] = {
        type: "choice",
        instructions: `Given the business requirements in \`requirements\`, which ${layer} technology is most suitable to build this software?`,
        criteria: options,
      };
    }
    for (const [id, c] of Object.entries(CLARIFY)) {
      questions[`clarify_${id}`] = { type: "noul", instructions: `${c.check} Consider \`requirements\`.` };
    }

    const start = Date.now();
    const upstream = await fetch(TYPESAFE_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: "jev-latest", state: { requirements: text.trim() }, questions }),
    });
    if (!upstream.ok) {
      // Pass TypeSafe's message through (e.g. a bad key) so the page can show it.
      const detail = (await upstream.text()).slice(0, 300);
      return json(upstream.status === 401 ? 401 : 502, { error: `TypeSafe ${upstream.status}: ${detail}` });
    }
    const data = (await upstream.json()) as SystemOneResponse;

    const layers: Record<string, [Array<[string, number]>, number]> = {};
    for (const layer of Object.keys(LAYERS)) {
      const a = data.answers[layer] as ChoiceAnswer;
      layers[layer] = [Object.entries(a.probabilities).sort((x, y) => y[1] - x[1]), a.confidence];
    }
    const clarify = Object.entries(CLARIFY)
      .filter(([id, c]) => (data.answers[`clarify_${id}`] as NoulAnswer).noul < c.threshold)
      .map(([id, c]) => ({ id, ask: c.ask, options: c.options }));

    return json(200, {
      layers,
      descriptions: LAYERS,
      clarify,
      model: data.model,
      tokens_in: data.usage.input_tokens,
      tokens_out: data.usage.output_tokens,
      ms: Date.now() - start,
    });
  },
};
