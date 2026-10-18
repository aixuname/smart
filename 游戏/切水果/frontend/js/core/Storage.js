const memory = new Map();
export const storage = {
  persistent: true,
  get(key, fallback = null) {
    try {
      const value = localStorage.getItem(key);
      if (value !== null) { memory.set(key, value); return value; }
    } catch (_) { this.persistent = false; }
    return memory.has(key) ? memory.get(key) : fallback;
  },
  set(key, value) {
    memory.set(key, value);
    try { localStorage.setItem(key, value); return true; }
    catch (_) { this.persistent = false; return false; }
  },
};

export function validRanks(value) {
  if (!Array.isArray(value)) return [];
  return value.filter(r => r && typeof r.name === 'string' && Number.isFinite(r.score) && r.score >= 0 &&
    Number.isFinite(r.date) && ['endless', 'timed', 'demo'].includes(r.mode))
    .map(r => ({ ...r, name: r.name.slice(0, 8), score: Math.floor(r.score) }));
}
