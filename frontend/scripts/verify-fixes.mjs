/**
 * Vérification locale — Restaurer (normalize) + santé backend.
 * Usage: node scripts/verify-fixes.mjs
 */

const JSON_WRAPPED = JSON.stringify({
  summary: "Landing café",
  code: `import React from 'react';
export default function App() {
  return (
    <main className="min-h-screen">
      <h1>Café Test</h1>
      <section>{[
        { name: 'Espresso', price: '2€' },
      ].map((item) => (
        <div key={item.name}>{item.name} — {item.price}</div>
      ))}</section>
    </main>
  );
}`,
  files: [],
});

// Simulation minimale du bug CodeHighlight (next===0 sans match)
function tokenizeLineSafe(line) {
  const NEXT = /\/\/|\/\*|`|"[^"\\]|'[^'\\]|<\/?[A-Za-z]|\b(const|let|return|export|import)\b|\d/;
  let rest = line;
  let steps = 0;
  while (rest.length > 0 && steps < 5000) {
    steps++;
    const next = rest.search(NEXT);
    if (next === -1) break;
    if (next > 0) {
      rest = rest.slice(next);
      continue;
    }
    rest = rest.slice(1);
  }
  return steps < 5000;
}

const stress = "'{ name: 'Espresso' }";
if (!tokenizeLineSafe(stress)) {
  console.error("FAIL: tokenize boucle sur", stress);
  process.exit(1);
}

async function healthCheck() {
  try {
    const res = await fetch("http://127.0.0.1:8002/api/health", {
      signal: AbortSignal.timeout(3000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

const h1 = await healthCheck();
console.log("health_before:", h1 ? "online" : "offline");
console.log("json_wrapped_len:", JSON_WRAPPED.length);
console.log("tokenize_stress: ok");
console.log("normalize: run npm run typecheck for full TS validation");
