import { h as head, s as store_get, c as unsubscribe_stores } from "../../chunks/index.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils2.js";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
import { i as isAuthenticated } from "../../chunks/auth.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    head("1uha8ag", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Baby Names — Find the perfect name together</title>`);
      });
    });
    $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[70dvh] text-center px-4"><div class="text-6xl mb-4 animate-bounce">👶</div> <h1 class="font-display font-extrabold text-3xl md:text-4xl text-[var(--color-text)] mb-2">Find the <span class="bg-gradient-to-r from-coral-500 via-lavender-500 to-ocean-500 bg-clip-text text-transparent">perfect</span> name</h1> <p class="text-[var(--color-text-muted)] text-lg max-w-sm mb-8">Browse thousands of names, rank your favourites, and decide together.</p> <div class="flex flex-col gap-3 w-full max-w-xs"><button class="btn-primary text-lg py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all">Start exploring 🔍</button> `);
    if (!store_get($$store_subs ??= {}, "$isAuthenticated", isAuthenticated)) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<p class="text-xs text-[var(--color-text-muted)]">Sign in to save your progress and compare with your partner</p>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> <div class="grid grid-cols-3 gap-4 mt-12 w-full max-w-sm"><div class="text-center"><div class="text-2xl mb-1">🔍</div> <div class="text-xs font-medium text-[var(--color-text-muted)]">Browse &amp; Filter</div></div> <div class="text-center"><div class="text-2xl mb-1">⚔️</div> <div class="text-xs font-medium text-[var(--color-text-muted)]">Head-to-Head</div></div> <div class="text-center"><div class="text-2xl mb-1">💕</div> <div class="text-xs font-medium text-[var(--color-text-muted)]">Compare Picks</div></div></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
