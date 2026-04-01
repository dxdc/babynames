<script lang="ts">
  import { goto } from '$app/navigation';
  import { isAuthenticated } from '$lib/stores/auth';
</script>

<svelte:head>
  <title>Baby Names — Find the perfect name together</title>
</svelte:head>

<div class="flex flex-col items-center justify-center min-h-[70dvh] text-center px-4">
  <div class="text-6xl mb-4 animate-bounce">👶</div>

  <h1 class="font-display font-extrabold text-3xl md:text-4xl text-[var(--color-text)] mb-2">
    Find the <span class="bg-gradient-to-r from-coral-500 via-lavender-500 to-ocean-500 bg-clip-text text-transparent">perfect</span> name
  </h1>

  <p class="text-[var(--color-text-muted)] text-lg max-w-sm mb-8">
    Browse thousands of names, rank your favourites, and decide together.
  </p>

  <div class="flex flex-col gap-3 w-full max-w-xs">
    <button
      onclick={() => goto('/browse')}
      class="btn-primary text-lg py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all"
    >
      Start exploring 🔍
    </button>

    {#if !$isAuthenticated}
      <p class="text-xs text-[var(--color-text-muted)]">
        Sign in to save your progress and compare with your partner
      </p>
    {/if}
  </div>

  <!-- Feature highlights -->
  <div class="grid grid-cols-3 gap-4 mt-12 w-full max-w-sm">
    <div class="text-center">
      <div class="text-2xl mb-1">🔍</div>
      <div class="text-xs font-medium text-[var(--color-text-muted)]">Browse &amp; Filter</div>
    </div>
    <div class="text-center">
      <div class="text-2xl mb-1">⚔️</div>
      <div class="text-xs font-medium text-[var(--color-text-muted)]">Head-to-Head</div>
    </div>
    <div class="text-center">
      <div class="text-2xl mb-1">💕</div>
      <div class="text-xs font-medium text-[var(--color-text-muted)]">Compare Picks</div>
    </div>
  </div>
</div>
