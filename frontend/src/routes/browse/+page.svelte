<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import FilterPanel from '$lib/components/FilterPanel.svelte';
  import NameCard from '$lib/components/NameCard.svelte';
  import { namesStore } from '$lib/stores/names';
  import { logger } from '$lib/utils/logger';

  const log = logger('BrowsePage');

  onMount(() => {
    namesStore.init();
    log.info('browse page mounted');
  });
</script>

<svelte:head>
  <title>Browse Names — Baby Names</title>
</svelte:head>

<div class="space-y-4">
  <div class="text-center py-2">
    <h1 class="font-display font-extrabold text-2xl text-[var(--color-text)]">
      Find the <span class="text-coral-500">perfect</span> name
    </h1>
    <p class="text-sm text-[var(--color-text-muted)] mt-1">
      {$namesStore.total.toLocaleString()} names to explore
    </p>
  </div>

  <FilterPanel
    origins={$namesStore.origins}
    currentFilters={$namesStore.filters}
  />

  <!-- Results -->
  <div class="space-y-2">
    {#if $namesStore.loading}
      <div class="text-center py-8">
        <div class="inline-block animate-spin text-3xl">🌀</div>
        <p class="text-sm text-[var(--color-text-muted)] mt-2">Finding names...</p>
      </div>
    {:else if $namesStore.error}
      <div class="card bg-red-50 border border-red-200 text-center py-6">
        <p class="text-red-700 font-medium">{$namesStore.error}</p>
        <button onclick={() => namesStore.init()} class="btn-primary mt-3 text-sm">
          Try again
        </button>
      </div>
    {:else if $namesStore.names.length === 0}
      <div class="text-center py-8">
        <span class="text-4xl">🤷</span>
        <p class="font-display font-bold text-lg mt-2 text-[var(--color-text)]">No names match</p>
        <p class="text-sm text-[var(--color-text-muted)] mt-1">Try broadening your filters</p>
      </div>
    {:else}
      {#each $namesStore.names as name (name.id)}
        <NameCard
          {name}
          onclick={() => goto(`/name/${name.id}`)}
        />
      {/each}

      <!-- Load more -->
      {#if $namesStore.page * $namesStore.perPage < $namesStore.total}
        <button
          onclick={() => namesStore.nextPage()}
          class="w-full py-3 rounded-xl bg-ocean-50 text-ocean-700 font-display font-semibold hover:bg-ocean-100 transition-all"
        >
          Load more ({$namesStore.total - $namesStore.page * $namesStore.perPage} remaining)
        </button>
      {/if}
    {/if}
  </div>
</div>
