// Regression check for stack_config.json: clarify thresholds and a few obvious picks.
// Usage: TYPESAFE_API_KEY=... node eval.mjs [base-url]   (default: local `wrangler dev`)
const BASE = process.argv[2] ?? "http://localhost:8787";
const KEY = process.env.TYPESAFE_API_KEY;
if (!KEY) throw new Error("set TYPESAFE_API_KEY");

// [prompt, clarify ids that should be asked, expected top picks]
const CASES = [
  ["Build me a trading mobile app that is very optimised for speed", ["scale"], { mobile: "!none" }],
  ["Internal HR leave tracker for 50 employees at a Microsoft-based company", ["platform"], {}],
  ["E-commerce storefront for a small bakery with online ordering", ["scale"], {}],
  ["IoT platform collecting temperature readings from 10,000 factory sensors", ["platform"], { database: "timeseries" }],
  ["Analytics dashboard over billions of ad-click events", [], { database: "warehouse" }],
  ["A real-time chat app for iOS and Android with millions of users", [], { mobile: "!none" }],
  ["I need software for my business", ["platform", "scale", "data"], {}],
  ["A website where 200 volunteers log their shift hours", [], { mobile: "!native" }],
  ["REST API for a logistics company to track parcel deliveries, about 5,000 requests per minute", [], {}],
  ["Desktop app for a dentist to manage patient records", ["scale"], {}],
  ["A tool to help our team collaborate better", ["platform", "scale", "data"], {}],
  ["Social network for pet owners to share photos", ["platform", "scale"], {}],
  ["Web portal for 3 million citizens to renew driving licences", [], {}],
  ["Build an app for booking yoga classes", ["platform", "scale"], {}],
  ["Internal dashboard showing sales numbers", ["scale"], {}],
];

let failures = 0;
for (const [prompt, wantAsk, wantPicks] of CASES) {
  const res = await fetch(`${BASE}/api/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-TypeSafe-Key": KEY },
    body: JSON.stringify({ requirements: prompt }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`${res.status} ${data.error}`);
  const asked = data.clarify.map((c) => c.id).sort();
  const errors = [];
  if (asked.join() !== [...wantAsk].sort().join()) errors.push(`asked [${asked}] want [${wantAsk}]`);
  for (const [layer, want] of Object.entries(wantPicks)) {
    const top = data.layers[layer][0][0][0];
    const ok = want.startsWith("!") ? top !== want.slice(1) : top === want;
    if (!ok) errors.push(`${layer}=${top} want ${want}`);
  }
  failures += errors.length > 0;
  console.log(errors.length ? "FAIL" : "ok  ", prompt.slice(0, 55), errors.join("; "));
}
console.log(`${CASES.length - failures}/${CASES.length} passed`);
process.exitCode = failures ? 1 : 0;
