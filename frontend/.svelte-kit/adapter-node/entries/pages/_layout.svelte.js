import { s as store_get, e as escape_html, a as ensure_array_like, b as attr, c as unsubscribe_stores } from "../../chunks/index.js";
import { i as isAuthenticated, c as currentUser } from "../../chunks/auth.js";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let { children } = $$props;
    const navItems = [
      { href: "/browse", label: "Browse", icon: "🔍" },
      { href: "/rank", label: "Rank", icon: "⚔️" },
      { href: "/leaderboard", label: "Top", icon: "🏆" },
      { href: "/favourites", label: "Favs", icon: "❤️" }
    ];
    $$renderer2.push(`<div class="min-h-dvh flex flex-col bg-[var(--color-bg)]"><header class="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-[var(--color-border)] px-4 py-2 flex items-center justify-between"><a href="/" class="flex items-center gap-2 no-underline"><span class="text-2xl">👶</span> <span class="font-display font-bold text-xl text-coral-600">Baby Names</span></a> <div>`);
    if (store_get($$store_subs ??= {}, "$isAuthenticated", isAuthenticated)) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<button class="text-sm text-[var(--color-text-muted)] hover:text-coral-600 transition-colors">${escape_html(store_get($$store_subs ??= {}, "$currentUser", currentUser)?.name)}</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<button class="btn-primary text-sm !px-4 !py-2">Sign in</button>`);
    }
    $$renderer2.push(`<!--]--></div></header> <main class="flex-1 px-4 py-4 max-w-2xl mx-auto w-full">`);
    children($$renderer2);
    $$renderer2.push(`<!----></main> <nav class="sticky bottom-0 z-50 bg-white/95 backdrop-blur-md border-t border-[var(--color-border)] flex justify-around py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden"><!--[-->`);
    const each_array = ensure_array_like(navItems);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let item = each_array[$$index];
      $$renderer2.push(`<a${attr("href", item.href)} class="flex flex-col items-center gap-0.5 text-[var(--color-text-muted)] hover:text-coral-600 transition-colors no-underline"><span class="text-xl">${escape_html(item.icon)}</span> <span class="text-xs font-medium">${escape_html(item.label)}</span></a>`);
    }
    $$renderer2.push(`<!--]--></nav></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
