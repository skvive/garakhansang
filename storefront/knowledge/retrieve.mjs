/**
 * Public, citation-bearing retrieval over approved FAQ data.
 * No LLM calls, no embeddings, no private source access.
 * Import from a server-side LEXID AI route after auth/permission checks.
 */
function normalize(value) {
  return String(value ?? "").normalize("NFKC").toLowerCase().replace(/[^가-힣a-z0-9]+/g, " ").trim();
}
function grams(value) {
  const words = normalize(value).split(/\s+/).filter(w => w.length >= 2);
  const result = new Set();
  for (const w of words) {
    result.add(w);
    if (w.length > 2) for (let i=0;i<=w.length-2;i++) result.add(w.slice(i,i+2));
  }
  return result;
}
export function searchPublicFaq(knowledge, query, options={}) {
  const limit = Math.max(1,Math.min(Number(options.limit)||3,10));
  const q = normalize(query);
  if (!q || !Array.isArray(knowledge?.entries)) return [];
  const needle = grams(q);
  if (!needle.size) return [];
  return knowledge.entries.map(item => {
    if (!item?.question || !item?.answer || !/^https:\/\/garakmall\.lexid\.site\//.test(item.source_url ?? "")) return null;
    const qt = grams(item.question), at = grams(item.answer);
    let score = normalize(item.question).includes(q) ? 20 : 0;
    for (const token of needle) score += qt.has(token) ? (token.length>2?4:2):at.has(token)?1:0;
    return score>=4 ? {id:item.id,question:item.question,answer:item.answer,citation_url:item.source_url,source_status:item.source_status,score} : null;
  }).filter(Boolean).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id)).slice(0,limit);
}
