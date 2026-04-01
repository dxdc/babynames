import { b as attr, a as ensure_array_like, d as attr_class, f as stringify, e as escape_html, i as derived, j as clsx, h as head, s as store_get, c as unsubscribe_stores } from "../../../chunks/index.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils2.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/state.svelte.js";
import { w as writable } from "../../../chunks/index2.js";
import { a as auth, l as logger } from "../../../chunks/auth.js";
const log$1 = logger("API");
const BASE_URL = "";
class ApiError extends Error {
  constructor(status, code, message, detail) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.name = "ApiError";
  }
}
async function request(method, path, options) {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (options?.params) {
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== void 0 && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const headers = {
    "Content-Type": "application/json"
  };
  const token = auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const fetchOptions = { method, headers };
  if (options?.body) {
    fetchOptions.body = JSON.stringify(options.body);
  }
  log$1.debug(`${method} ${path}`, { params: options?.params });
  const resp = await fetch(url.toString(), fetchOptions);
  if (!resp.ok) {
    let errorBody = {};
    try {
      errorBody = await resp.json();
    } catch {
    }
    const error = new ApiError(
      resp.status,
      errorBody.error || "unknown_error",
      errorBody.message || `Request failed: ${resp.status}`,
      errorBody.detail
    );
    log$1.error(`${method} ${path} → ${resp.status}`, { error: error.message });
    throw error;
  }
  const data = await resp.json();
  log$1.debug(`${method} ${path} → ${resp.status}`, { data });
  return data;
}
const api = {
  // Names
  getNames: (filters) => request("GET", "/api/names", { params: filters }),
  getName: (id) => request("GET", `/api/names/${id}`),
  getOrigins: () => request("GET", "/api/origins"),
  // Ranking
  getLeaderboard: (params) => request("GET", "/api/ranking/leaderboard", { params }),
  getPair: (filters) => request("GET", "/api/ranking/pair", { params: filters }),
  submitComparison: (winnerId, loserId, roundLabel) => request("POST", "/api/ranking/compare", {
    body: { winner_id: winnerId, loser_id: loserId, round_label: roundLabel }
  }),
  // Favourites
  getFavourites: () => request("GET", "/api/favourites"),
  addFavourite: (nameId, note) => request("POST", "/api/favourites", { body: { name_id: nameId, note } }),
  removeFavourite: (nameId) => request("DELETE", `/api/favourites/${nameId}`),
  updateFavouriteNote: (nameId, note) => request("PATCH", `/api/favourites/${nameId}`, { body: { note } }),
  // Sessions
  createSession: () => request("POST", "/api/sessions"),
  joinSession: (inviteCode) => request("POST", "/api/sessions/join", { body: { invite_code: inviteCode } }),
  getSessionComparison: (sessionId) => request("GET", `/api/sessions/${sessionId}/compare`)
};
const log = logger("NamesStore");
const DEFAULT_FILTERS = {
  sort: "rank",
  page: 1,
  per_page: 50
};
function createNamesStore() {
  const initial = {
    names: [],
    total: 0,
    page: 1,
    perPage: 50,
    loading: false,
    error: null,
    origins: [],
    filters: { ...DEFAULT_FILTERS }
  };
  const { subscribe, set, update } = writable(initial);
  let currentRequest = null;
  async function fetchNames(filters) {
    if (currentRequest) currentRequest.abort();
    currentRequest = new AbortController();
    update((s) => ({ ...s, loading: true, error: null, filters }));
    log.info("fetching names", { filters });
    try {
      const resp = await api.getNames(filters);
      update((s) => ({
        ...s,
        names: resp.names,
        total: resp.total,
        page: resp.page,
        perPage: resp.per_page,
        loading: false
      }));
      log.info("names loaded", { count: resp.names.length, total: resp.total });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const msg = err instanceof Error ? err.message : "Failed to load names";
      log.error("fetch failed", { error: msg });
      update((s) => ({ ...s, loading: false, error: msg }));
    }
  }
  async function fetchOrigins() {
    try {
      const resp = await api.getOrigins();
      update((s) => ({ ...s, origins: resp.origins }));
      log.info("origins loaded", { count: resp.origins.length });
    } catch (err) {
      log.error("origins fetch failed", { error: err });
    }
  }
  return {
    subscribe,
    init() {
      fetchOrigins();
      fetchNames(DEFAULT_FILTERS);
    },
    setFilters(newFilters) {
      update((s) => {
        const merged = { ...s.filters, ...newFilters, page: 1 };
        fetchNames(merged);
        return { ...s, filters: merged };
      });
    },
    clearFilters() {
      fetchNames({ ...DEFAULT_FILTERS });
    },
    loadPage(page) {
      update((s) => {
        const filters = { ...s.filters, page };
        fetchNames(filters);
        return s;
      });
    },
    nextPage() {
      update((s) => {
        if (s.page * s.perPage < s.total) {
          const filters = { ...s.filters, page: s.page + 1 };
          fetchNames(filters);
        }
        return s;
      });
    }
  };
}
const namesStore = createNamesStore();
function FilterPanel($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { origins, currentFilters } = $$props;
    let searchQuery = currentFilters.q || "";
    let selectedGender = currentFilters.gender || "";
    let selectedOrigins = currentFilters.origins ? currentFilters.origins.split(",") : [];
    let eraStart = currentFilters.era_start?.toString() || "";
    let eraEnd = currentFilters.era_end?.toString() || "";
    currentFilters.sort || "rank";
    const hasActiveFilters = derived(() => !!searchQuery || !!selectedGender || selectedOrigins.length > 0 || !!eraStart || !!eraEnd);
    $$renderer2.push(`<div class="space-y-3"><div class="relative"><input type="text" placeholder="Search names..."${attr("value", searchQuery)} class="w-full px-4 py-3 rounded-xl bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-coral-300 focus:border-coral-400 font-body transition-all"/> `);
    if (searchQuery) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<button class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-coral-600 transition-colors">✕</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> <div class="flex gap-2"><!--[-->`);
    const each_array = ensure_array_like([
      { key: "F", label: "👧 Girl", cls: "coral" },
      { key: "M", label: "👦 Boy", cls: "ocean" },
      { key: "U", label: "🌟 Unisex", cls: "mint" }
    ]);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let g = each_array[$$index];
      $$renderer2.push(`<button${attr_class(`flex-1 py-2 rounded-xl text-sm font-display font-semibold transition-all ${stringify(selectedGender === g.key ? `bg-${g.cls}-500 text-white shadow-md` : `bg-${g.cls}-50 text-${g.cls}-700 hover:bg-${g.cls}-100`)}`)}>${escape_html(g.label)}</button>`);
    }
    $$renderer2.push(`<!--]--></div> `);
    if (origins.length > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div><div class="text-xs font-medium text-[var(--color-text-muted)] mb-1.5 uppercase tracking-wide">Origin</div> <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto"><!--[-->`);
      const each_array_1 = ensure_array_like(origins.slice(0, 20));
      for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
        let origin = each_array_1[$$index_1];
        $$renderer2.push(`<button${attr_class(`px-3 py-1 rounded-full text-xs font-medium transition-all ${stringify(selectedOrigins.includes(origin.slug) ? "bg-lavender-500 text-white" : "bg-lavender-50 text-lavender-700 hover:bg-lavender-100")}`)}>${escape_html(origin.name)} <span class="opacity-60">(${escape_html(origin.name_count)})</span></button>`);
      }
      $$renderer2.push(`<!--]--> `);
      if (origins.length > 20) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<button class="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all">+${escape_html(origins.length - 20)} more</button>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <button class="text-sm text-[var(--color-text-muted)] hover:text-coral-600 transition-colors">${escape_html("▸ More filters")}</button> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (hasActiveFilters()) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<button class="text-sm text-coral-600 hover:text-coral-700 font-medium transition-colors">Clear all filters</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
function NameCard($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { name, compact = false } = $$props;
    const genderBadge = derived(() => name.gender === "M" ? "badge-gender-m" : name.gender === "F" ? "badge-gender-f" : "badge-gender-u");
    const genderLabel = derived(() => name.gender === "M" ? "Boy" : name.gender === "F" ? "Girl" : "Unisex");
    $$renderer2.push(`<button${attr_class(`card w-full text-left group cursor-pointer border-0 ${stringify(compact ? "p-3" : "p-4")}`)}><div class="flex items-start justify-between gap-3"><div class="flex-1 min-w-0"><div class="flex items-center gap-2 mb-1"><h3${attr_class(`font-display font-bold ${stringify(compact ? "text-lg" : "text-xl")} text-[var(--color-text)] group-hover:text-coral-600 transition-colors truncate`)}>${escape_html(name.display_name)}</h3> <span${attr_class(clsx(genderBadge()))}>${escape_html(genderLabel())}</span></div> `);
    if (name.meaning_short && !compact) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<p class="text-sm text-[var(--color-text-muted)] line-clamp-2 mb-2">${escape_html(name.meaning_short)}</p>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="flex flex-wrap gap-1.5"><!--[-->`);
    const each_array = ensure_array_like(name.origins.slice(0, 3));
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let origin = each_array[$$index];
      $$renderer2.push(`<span class="badge-origin">${escape_html(origin)}</span>`);
    }
    $$renderer2.push(`<!--]--> `);
    if (name.origins.length > 3) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span class="badge-origin">+${escape_html(name.origins.length - 3)}</span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></div> <div class="text-right flex-shrink-0">`);
    if (name.year_peak) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="text-xs text-[var(--color-text-muted)]">Peak</div> <div class="font-display font-bold text-sm text-lavender-600">${escape_html(name.year_peak)}</div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></div></button>`);
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    head("1kxy863", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Browse Names — Baby Names</title>`);
      });
    });
    $$renderer2.push(`<div class="space-y-4"><div class="text-center py-2"><h1 class="font-display font-extrabold text-2xl text-[var(--color-text)]">Find the <span class="text-coral-500">perfect</span> name</h1> <p class="text-sm text-[var(--color-text-muted)] mt-1">${escape_html(store_get($$store_subs ??= {}, "$namesStore", namesStore).total.toLocaleString())} names to explore</p></div> `);
    FilterPanel($$renderer2, {
      origins: store_get($$store_subs ??= {}, "$namesStore", namesStore).origins,
      currentFilters: store_get($$store_subs ??= {}, "$namesStore", namesStore).filters
    });
    $$renderer2.push(`<!----> <div class="space-y-2">`);
    if (store_get($$store_subs ??= {}, "$namesStore", namesStore).loading) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="text-center py-8"><div class="inline-block animate-spin text-3xl">🌀</div> <p class="text-sm text-[var(--color-text-muted)] mt-2">Finding names...</p></div>`);
    } else if (store_get($$store_subs ??= {}, "$namesStore", namesStore).error) {
      $$renderer2.push("<!--[1-->");
      $$renderer2.push(`<div class="card bg-red-50 border border-red-200 text-center py-6"><p class="text-red-700 font-medium">${escape_html(store_get($$store_subs ??= {}, "$namesStore", namesStore).error)}</p> <button class="btn-primary mt-3 text-sm">Try again</button></div>`);
    } else if (store_get($$store_subs ??= {}, "$namesStore", namesStore).names.length === 0) {
      $$renderer2.push("<!--[2-->");
      $$renderer2.push(`<div class="text-center py-8"><span class="text-4xl">🤷</span> <p class="font-display font-bold text-lg mt-2 text-[var(--color-text)]">No names match</p> <p class="text-sm text-[var(--color-text-muted)] mt-1">Try broadening your filters</p></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<!--[-->`);
      const each_array = ensure_array_like(store_get($$store_subs ??= {}, "$namesStore", namesStore).names);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let name = each_array[$$index];
        NameCard($$renderer2, { name });
      }
      $$renderer2.push(`<!--]--> `);
      if (store_get($$store_subs ??= {}, "$namesStore", namesStore).page * store_get($$store_subs ??= {}, "$namesStore", namesStore).perPage < store_get($$store_subs ??= {}, "$namesStore", namesStore).total) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<button class="w-full py-3 rounded-xl bg-ocean-50 text-ocean-700 font-display font-semibold hover:bg-ocean-100 transition-all">Load more (${escape_html(store_get($$store_subs ??= {}, "$namesStore", namesStore).total - store_get($$store_subs ??= {}, "$namesStore", namesStore).page * store_get($$store_subs ??= {}, "$namesStore", namesStore).perPage)} remaining)</button>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
