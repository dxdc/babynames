<script lang="ts">
  import '../app.css';
  import { auth, isAuthenticated, currentUser } from '$lib/stores/auth';
  import { logger } from '$lib/utils/logger';

  const log = logger('Layout');

  let { children } = $props();

  const navItems = [
    { href: '/browse', label: 'Browse', icon: '🔍' },
    { href: '/rank', label: 'Rank', icon: '⚔️' },
    { href: '/leaderboard', label: 'Top', icon: '🏆' },
    { href: '/favourites', label: 'Favs', icon: '❤️' },
  ];
</script>

<div class="min-h-dvh flex flex-col bg-[var(--color-bg)]">
  <!-- Top bar -->
  <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-[var(--color-border)] px-4 py-2 flex items-center justify-between">
    <a href="/" class="flex items-center gap-2 no-underline">
      <span class="text-2xl">👶</span>
      <span class="font-display font-bold text-xl text-coral-600">Baby Names</span>
    </a>

    <div>
      {#if $isAuthenticated}
        <button
          onclick={() => auth.logout()}
          class="text-sm text-[var(--color-text-muted)] hover:text-coral-600 transition-colors"
        >
          {$currentUser?.name}
        </button>
      {:else}
        <button onclick={() => auth.login()} class="btn-primary text-sm !px-4 !py-2">
          Sign in
        </button>
      {/if}
    </div>
  </header>

  <!-- Main content -->
  <main class="flex-1 px-4 py-4 max-w-2xl mx-auto w-full">
    {@render children()}
  </main>

  <!-- Bottom nav (mobile) -->
  <nav class="sticky bottom-0 z-50 bg-white/95 backdrop-blur-md border-t border-[var(--color-border)] flex justify-around py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden">
    {#each navItems as item}
      <a
        href={item.href}
        class="flex flex-col items-center gap-0.5 text-[var(--color-text-muted)] hover:text-coral-600 transition-colors no-underline"
      >
        <span class="text-xl">{item.icon}</span>
        <span class="text-xs font-medium">{item.label}</span>
      </a>
    {/each}
  </nav>
</div>
