// Global test setup
// Node 26 + jsdom 26 兼容垫片：确保 localStorage 在测试环境可用
class MemoryStorage {
  store = new Map();
  get length() { return this.store.size; }
  key(index) { return [...this.store.keys()][index] ?? null; }
  getItem(key) { return this.store.has(key) ? this.store.get(key) : null; }
  setItem(key, value) { this.store.set(String(key), String(value)); }
  removeItem(key) { this.store.delete(key); }
  clear() { this.store.clear(); }
}

{
  const storage = new MemoryStorage();
  const g = globalThis;
  if (g.localStorage === undefined) Object.defineProperty(g, 'localStorage', { value: storage, configurable: true });
  if (g.sessionStorage === undefined) Object.defineProperty(g, 'sessionStorage', { value: new MemoryStorage(), configurable: true });
  if (typeof window !== 'undefined') {
    if (window.localStorage === undefined) Object.defineProperty(window, 'localStorage', { value: storage, configurable: true });
    if (window.sessionStorage === undefined) Object.defineProperty(window, 'sessionStorage', { value: new MemoryStorage(), configurable: true });
  }
}
