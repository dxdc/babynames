// Baby Names - ELO Battle Mode
// Head-to-head name comparisons with ELO rating system,
// veto list, convergence detection, and multi-session persistence.

const elo = (() => {
  "use strict";

  // ---------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------

  const K_FACTOR = 32; // Standard ELO K-factor
  const INITIAL_RATING = 1500;
  const STORAGE_PREFIX = "bn_elo_";
  const MIN_COMPARISONS_FOR_STABLE = 8; // Name needs this many comparisons to be "stable"
  const CONVERGENCE_THRESHOLD = 0.85; // 85% of top-20 names stable = converged

  // ---------------------------------------------------------------
  // Mutable state
  // ---------------------------------------------------------------

  let pool = []; // Names eligible for battle (filtered, no vetoes)
  let ratings = {}; // rank -> { rating, wins, losses, comparisons, name }
  let vetoes = {}; // name (lowercase) -> true
  let history = []; // { winner: rank, loser: rank, timestamp }
  let sessionId = "";
  let totalComparisons = 0;
  let currentPair = null; // { left: row, right: row }
  let voterName = "";

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------

  const $ = (id) => document.getElementById(id);

  const getGender = () =>
    typeof getCurrentGender === "function" ? getCurrentGender() : "M";

  function expectedScore(ratingA, ratingB) {
    return 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
  }

  function updateRatings(winnerRank, loserRank) {
    const w = ratings[winnerRank];
    const l = ratings[loserRank];
    if (!w || !l) return;

    const expectedW = expectedScore(w.rating, l.rating);
    const expectedL = expectedScore(l.rating, w.rating);

    w.rating = Math.round(w.rating + K_FACTOR * (1 - expectedW));
    l.rating = Math.round(l.rating + K_FACTOR * (0 - expectedL));
    w.wins++;
    l.losses++;
    w.comparisons++;
    l.comparisons++;
  }

  // Pick a pair that maximises information gain:
  // Prefer names with fewer comparisons, and names with similar ratings
  function pickPair() {
    if (pool.length < 2) return null;

    // Weight names by inverse of comparisons (explore under-compared names)
    const weighted = pool.map((row) => {
      const r = ratings[row.rank];
      const comps = r ? r.comparisons : 0;
      return { row, weight: 1 / (1 + comps) };
    });

    // Pick first name weighted by exploration need
    const totalWeight = weighted.reduce((s, w) => s + w.weight, 0);
    let pick1 = pickWeighted(weighted, totalWeight);

    // Pick second name: prefer similar rating for more informative matchup
    const r1 = (ratings[pick1.rank] || {}).rating || INITIAL_RATING;
    const candidates = weighted.filter((w) => w.row.rank !== pick1.rank);

    // Sort by rating proximity, take top 10, then pick randomly from those
    candidates.sort((a, b) => {
      const ra = (ratings[a.row.rank] || {}).rating || INITIAL_RATING;
      const rb = (ratings[b.row.rank] || {}).rating || INITIAL_RATING;
      return Math.abs(ra - r1) - Math.abs(rb - r1);
    });

    const topN = candidates.slice(0, Math.min(10, candidates.length));
    const pick2 = topN[Math.floor(Math.random() * topN.length)].row;

    return { left: pick1, right: pick2 };
  }

  function pickWeighted(items, totalWeight) {
    let r = Math.random() * totalWeight;
    for (const item of items) {
      r -= item.weight;
      if (r <= 0) return item.row;
    }
    return items[items.length - 1].row;
  }

  // ---------------------------------------------------------------
  // Convergence detection
  // ---------------------------------------------------------------

  function getLeaderboard(n = 20) {
    const entries = Object.entries(ratings)
      .map(([rank, data]) => ({ rank: Number(rank), ...data }))
      .filter((e) => e.comparisons > 0)
      .sort((a, b) => b.rating - a.rating);
    return entries.slice(0, n);
  }

  function getConvergenceInfo() {
    const top = getLeaderboard(20);
    if (top.length < 5) return { converged: false, pct: 0, stable: 0, total: top.length };

    const stable = top.filter((e) => e.comparisons >= MIN_COMPARISONS_FOR_STABLE).length;
    const pct = stable / top.length;
    return {
      converged: pct >= CONVERGENCE_THRESHOLD,
      pct: Math.round(pct * 100),
      stable,
      total: top.length,
    };
  }

  // ---------------------------------------------------------------
  // Veto list
  // ---------------------------------------------------------------

  function addVeto(name) {
    vetoes[name.toLowerCase()] = true;
    rebuildPool();
    saveSession();
  }

  function removeVeto(name) {
    delete vetoes[name.toLowerCase()];
    rebuildPool();
    saveSession();
  }

  function isVetoed(row) {
    const name = row.name.toLowerCase();
    if (vetoes[name]) return true;
    // Also check spelling variants
    if (row.spelling_variants) {
      for (const v of row.spelling_variants.split(" ")) {
        if (v && vetoes[v.toLowerCase()]) return true;
      }
    }
    return false;
  }

  function rebuildPool() {
    const allData = typeof getSwipeDeck === "function" ? getSwipeDeck() : [];
    pool = allData.filter((row) => !isVetoed(row));
  }

  // ---------------------------------------------------------------
  // Persistence
  // ---------------------------------------------------------------

  function saveSession() {
    const data = {
      ratings,
      vetoes,
      history: history.slice(-500), // Keep last 500
      totalComparisons,
      voterName,
    };
    try {
      localStorage.setItem(sessionId, JSON.stringify(data));
    } catch {
      // Storage full — drop oldest history
      data.history = data.history.slice(-100);
      try {
        localStorage.setItem(sessionId, JSON.stringify(data));
      } catch { /* give up */ }
    }
  }

  function loadSession() {
    try {
      const raw = localStorage.getItem(sessionId);
      if (!raw) return;
      const data = JSON.parse(raw);
      ratings = data.ratings || {};
      vetoes = data.vetoes || {};
      history = data.history || [];
      totalComparisons = data.totalComparisons || 0;
      voterName = data.voterName || "";
    } catch {
      // Corrupted — start fresh
      ratings = {};
      vetoes = {};
      history = [];
      totalComparisons = 0;
    }
  }

  // ---------------------------------------------------------------
  // Screens
  // ---------------------------------------------------------------

  const SCREENS = ["elo-intro", "elo-battle", "elo-results"];

  function showScreen(id) {
    for (const s of SCREENS) $(s).style.display = s === id ? "" : "none";
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------

  function init() {
    $("elo-launch").addEventListener("click", openElo);
    $("elo-close").addEventListener("click", closeElo);
    $("elo-start-btn").addEventListener("click", startBattling);
    $("elo-start-fresh").addEventListener("click", startFresh);
    $("elo-left-card").addEventListener("click", () => pickWinner("left"));
    $("elo-right-card").addEventListener("click", () => pickWinner("right"));
    $("elo-skip-btn").addEventListener("click", skipPair);
    $("elo-leaderboard-btn").addEventListener("click", showResults);
    $("elo-results-close").addEventListener("click", () => {
      showScreen("elo-battle");
      nextBattle();
    });
    $("elo-results-done").addEventListener("click", closeElo);

    // Veto management
    $("elo-veto-add-btn").addEventListener("click", addVetoFromInput);
    $("elo-veto-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addVetoFromInput();
    });

    // Keyboard controls
    document.addEventListener("keydown", (e) => {
      if ($("elo-overlay").style.display === "none") return;
      if ($("elo-battle").style.display === "none") return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        pickWinner("left");
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        pickWinner("right");
      } else if (e.key === "s" || e.key === "ArrowDown") {
        e.preventDefault();
        skipPair();
      }
    });

    $("elo-voter-name").addEventListener("change", function () {
      voterName = this.value.trim();
      saveSession();
    });

    // Sharing
    $("elo-share-btn").addEventListener("click", shareRankings);
    $("elo-add-partner-btn").addEventListener("click", () => {
      const row = $("elo-partner-input-row");
      row.style.display = row.style.display === "none" ? "" : "none";
      $("elo-partner-url").value = "";
      $("elo-partner-url").focus();
    });
    $("elo-partner-go").addEventListener("click", loadPartnerFromInput);
    $("elo-partner-url").addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadPartnerFromInput();
    });
  }

  // ---------------------------------------------------------------
  // Open / Close
  // ---------------------------------------------------------------

  function openElo() {
    sessionId = `${STORAGE_PREFIX}${getGender()}`;
    loadSession();
    rebuildPool();

    // Ensure all pool names have ratings
    for (const row of pool) {
      if (!ratings[row.rank]) {
        ratings[row.rank] = {
          rating: INITIAL_RATING,
          wins: 0,
          losses: 0,
          comparisons: 0,
          name: row.name,
        };
      }
    }

    $("elo-overlay").style.display = "";
    showIntro();
    document.body.style.overflow = "hidden";
  }

  function closeElo() {
    $("elo-overlay").style.display = "none";
    for (const s of SCREENS) $(s).style.display = "none";
    document.body.style.overflow = "";
  }

  // ---------------------------------------------------------------
  // Intro
  // ---------------------------------------------------------------

  function showIntro() {
    showScreen("elo-intro");

    $("elo-voter-name").value = voterName;
    $("elo-pool-size").textContent = pool.length.toLocaleString();

    // Resume info
    if (totalComparisons > 0) {
      const top3 = getLeaderboard(3);
      const topNames = top3.map((e) => e.name).join(", ");
      $("elo-resume-info").textContent =
        `${totalComparisons} comparisons · Top: ${topNames}`;
      $("elo-resume-info").style.display = "";
      $("elo-start-fresh").style.display = "";
    } else {
      $("elo-resume-info").style.display = "none";
      $("elo-start-fresh").style.display = "none";
    }

    renderVetoList();
  }

  function renderVetoList() {
    const container = $("elo-veto-list");
    container.innerHTML = "";
    const names = Object.keys(vetoes).sort();
    if (!names.length) {
      container.innerHTML = '<span class="elo-veto-empty">No vetoed names</span>';
      return;
    }
    for (const name of names) {
      const chip = document.createElement("span");
      chip.className = "elo-veto-chip";
      chip.innerHTML =
        `${name} <button class="elo-veto-remove" data-name="${name}">×</button>`;
      chip.querySelector("button").addEventListener("click", () => {
        removeVeto(name);
        renderVetoList();
        $("elo-pool-size").textContent = pool.length.toLocaleString();
      });
      container.appendChild(chip);
    }
  }

  function addVetoFromInput() {
    const input = $("elo-veto-input");
    const name = input.value.trim();
    if (!name) return;
    addVeto(name);
    input.value = "";
    renderVetoList();
    $("elo-pool-size").textContent = pool.length.toLocaleString();
  }

  // ---------------------------------------------------------------
  // Battle
  // ---------------------------------------------------------------

  function startFresh() {
    ratings = {};
    vetoes = {};
    history = [];
    totalComparisons = 0;
    rebuildPool();
    for (const row of pool) {
      ratings[row.rank] = {
        rating: INITIAL_RATING,
        wins: 0,
        losses: 0,
        comparisons: 0,
        name: row.name,
      };
    }
    saveSession();
    startBattling();
  }

  function startBattling() {
    const nameInput = $("elo-voter-name");
    if (nameInput && nameInput.value.trim()) {
      voterName = nameInput.value.trim();
      saveSession();
    }
    showScreen("elo-battle");
    nextBattle();
  }

  function nextBattle() {
    currentPair = pickPair();
    if (!currentPair) {
      showResults();
      return;
    }
    renderBattle();
  }

  function renderBattle() {
    if (!currentPair) return;

    const { left, right } = currentPair;

    // Left card
    $("elo-left-name").textContent = left.name;
    $("elo-left-stats").textContent = buildStats(left);
    $("elo-left-rating").textContent = `${(ratings[left.rank] || {}).rating || INITIAL_RATING}`;
    renderBadges($("elo-left-badges"), left);

    // Right card
    $("elo-right-name").textContent = right.name;
    $("elo-right-stats").textContent = buildStats(right);
    $("elo-right-rating").textContent = `${(ratings[right.rank] || {}).rating || INITIAL_RATING}`;
    renderBadges($("elo-right-badges"), right);

    // Progress
    $("elo-comparison-count").textContent = totalComparisons.toLocaleString();

    // Convergence
    const conv = getConvergenceInfo();
    const convEl = $("elo-convergence");
    if (totalComparisons >= 20) {
      convEl.style.display = "";
      convEl.textContent = conv.converged
        ? `Converged! Top names are stable.`
        : `Stability: ${conv.pct}% (${conv.stable}/${conv.total} top names settled)`;
      convEl.className = `elo-convergence ${conv.converged ? "converged" : ""}`;
    } else {
      convEl.style.display = "none";
    }

    // Top 3 preview
    const top3 = getLeaderboard(3);
    $("elo-top-preview").textContent = top3.length
      ? `Leading: ${top3.map((e) => `${e.name} (${e.rating})`).join(" · ")}`
      : "";

    // Animate cards in
    for (const id of ["elo-left-card", "elo-right-card"]) {
      const el = $(id);
      el.style.transition = "transform 0.25s ease, opacity 0.2s ease";
      el.style.transform = "scale(0.93)";
      el.style.opacity = "0.5";
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          el.style.transform = "";
          el.style.opacity = "1";
        });
      });
    }
  }

  function buildStats(row) {
    const parts = [`#${row.rank}`];
    if (row.total_count) parts.push(`${Number(row.total_count).toLocaleString()}`);
    if (row.year_peak) parts.push(`peak ${row.year_peak}`);
    if (row.syllables) parts.push(`${row.syllables} syl`);
    return parts.join(" · ");
  }

  function renderBadges(container, row) {
    container.innerHTML = "";
    const badges = [];
    if (row.biblical) badges.push({ icon: "📖", label: row.biblical === "Place" ? "Biblical Place" : "Biblical" });
    const yr = new Date().getFullYear();
    if (row.year_peak && row.year_peak >= yr - 15) badges.push({ icon: "📈", label: "Trending" });
    else if (row.year_peak && row.year_peak < 1960) badges.push({ icon: "🕰️", label: "Classic" });
    if (row.nickname_of) {
      const nicks = row.nickname_of.split(" ");
      badges.push({ icon: "💬", label: `Short for ${nicks.slice(0, 3).join(", ")}` });
    }
    for (const b of badges) {
      const span = document.createElement("span");
      span.className = "elo-badge";
      span.innerHTML = `<span class="badge-icon">${b.icon}</span>${b.label}`;
      container.appendChild(span);
    }
  }

  function pickWinner(side) {
    if (!currentPair) return;

    const winner = side === "left" ? currentPair.left : currentPair.right;
    const loser = side === "left" ? currentPair.right : currentPair.left;

    updateRatings(winner.rank, loser.rank);
    totalComparisons++;

    history.push({
      winner: winner.rank,
      loser: loser.rank,
      timestamp: Date.now(),
    });

    // Flash winner card
    const winCard = $(side === "left" ? "elo-left-card" : "elo-right-card");
    const loseCard = $(side === "left" ? "elo-right-card" : "elo-left-card");
    winCard.classList.add("elo-card-win");
    loseCard.classList.add("elo-card-lose");
    setTimeout(() => {
      winCard.classList.remove("elo-card-win");
      loseCard.classList.remove("elo-card-lose");
    }, 300);

    saveSession();

    setTimeout(() => nextBattle(), 300);
  }

  function skipPair() {
    nextBattle();
  }

  // ---------------------------------------------------------------
  // Results / Leaderboard
  // ---------------------------------------------------------------

  function showResults() {
    showScreen("elo-results");

    const board = getLeaderboard(50);
    const container = $("elo-leaderboard");
    container.innerHTML = "";

    if (!board.length) {
      container.innerHTML = '<div class="elo-empty">No ratings yet. Start battling!</div>';
      return;
    }

    // Stats header
    const conv = getConvergenceInfo();
    $("elo-results-stats").textContent =
      `${totalComparisons} comparisons · ${pool.length.toLocaleString()} names in pool · ` +
      `Stability: ${conv.pct}%`;

    for (let i = 0; i < board.length; i++) {
      const entry = board[i];
      const row = document.createElement("div");
      row.className = "elo-lb-row";
      if (i < 3) row.classList.add("elo-lb-top3");

      const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}.`;

      row.innerHTML =
        `<span class="elo-lb-rank">${medal}</span>` +
        `<span class="elo-lb-name">${entry.name}</span>` +
        `<span class="elo-lb-rating">${entry.rating}</span>` +
        `<span class="elo-lb-record">${entry.wins}W ${entry.losses}L</span>` +
        `<span class="elo-lb-stable">${entry.comparisons >= MIN_COMPARISONS_FOR_STABLE ? "✓" : "…"}</span>`;

      container.appendChild(row);
    }

    renderComparison();
  }

  // ---------------------------------------------------------------
  // Sharing — encode top-N rankings as URL, load partner's rankings
  // ---------------------------------------------------------------

  let partnerData = []; // [{ name, gender, rankings: [{ rank, name, rating }] }]

  function safeEncode(str) {
    return btoa(
      Array.from(new TextEncoder().encode(str), (b) =>
        String.fromCharCode(b),
      ).join(""),
    );
  }

  function safeDecode(str) {
    return new TextDecoder().decode(
      Uint8Array.from(atob(str), (c) => c.charCodeAt(0)),
    );
  }

  function encodeRankings() {
    const top = getLeaderboard(30);
    return safeEncode(
      JSON.stringify({
        n: voterName || "Partner",
        g: getGender(),
        t: top.map((e) => ({ r: e.rank, n: e.name, s: e.rating })),
      }),
    );
  }

  function decodeRankings(encoded) {
    try {
      return JSON.parse(safeDecode(encoded));
    } catch {
      return null;
    }
  }

  function shareRankings() {
    if (!voterName) {
      const name = prompt("Enter your name (so your partner knows whose rankings these are):");
      if (!name) return;
      voterName = name.trim();
      saveSession();
      $("elo-voter-name").value = voterName;
    }
    const top = getLeaderboard(30);
    if (!top.length) {
      alert("No rankings yet — do some battles first!");
      return;
    }
    const encoded = encodeRankings();
    const url = `${location.origin}${location.pathname}#elo=${encoded}`;
    if (navigator.share) {
      navigator.share({
        title: `${voterName}'s name rankings`,
        text: `${voterName} shared their top ${top.length} baby name rankings`,
        url,
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(
        () => showToast("Link copied!"),
        () => prompt("Copy this link:", url),
      );
    }
  }

  function showToast(message) {
    const existing = document.querySelector(".elo-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.className = "elo-toast";
    toast.textContent = message;
    $("elo-overlay").appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  function loadPartnerFromInput() {
    const input = $("elo-partner-url").value.trim();
    if (!input) return;
    try {
      const hashPart = input.includes("#") ? input.split("#")[1] : input;
      const encoded = hashPart.startsWith("elo=") ? hashPart.slice(4) : hashPart;
      const data = decodeRankings(encoded);
      if (!data || !data.t || !data.t.length) throw new Error("bad data");

      if (data.g && data.g !== getGender()) {
        const label = data.g === "M" ? "boys" : "girls";
        const current = getGender() === "M" ? "boys" : "girls";
        alert(`Those rankings are for ${label}, but you're viewing ${current}. Switch gender first.`);
        return;
      }

      if (voterName && data.n === voterName) {
        alert("That's your own rankings link!");
        return;
      }

      const partner = {
        name: data.n || "Partner",
        gender: data.g,
        rankings: data.t.map((e) => ({ rank: e.r, name: e.n, rating: e.s })),
      };

      // Replace existing partner with same name
      partnerData = partnerData.filter((p) => p.name !== partner.name);
      partnerData.push(partner);

      $("elo-partner-input-row").style.display = "none";
      showToast(`Loaded ${partner.name}'s top ${partner.rankings.length} rankings`);
      showResults();
    } catch {
      alert("Could not read rankings. Make sure you paste the full link.");
    }
  }

  function detectPartnerFromHash() {
    const hash = location.hash;
    if (!hash.includes("elo=")) return;
    const encoded = hash.split("elo=")[1];
    if (!encoded) return;
    const data = decodeRankings(encoded);
    if (!data || !data.t) return;
    partnerData.push({
      name: data.n || "Partner",
      gender: data.g,
      rankings: data.t.map((e) => ({ rank: e.r, name: e.n, rating: e.s })),
    });
    // Clean the hash so it doesn't reload on refresh
    history.replaceState(null, "", location.pathname + location.search);
  }

  function renderComparison() {
    const container = $("elo-compare-results");
    container.innerHTML = "";

    if (!partnerData.length) {
      $("elo-compare-section").style.display = "none";
      return;
    }

    $("elo-compare-section").style.display = "";
    const myTop = getLeaderboard(30);
    const myNames = new Map(myTop.map((e, i) => [e.name, { position: i + 1, rating: e.rating }]));

    for (const partner of partnerData) {
      const heading = document.createElement("h4");
      heading.textContent = `You + ${partner.name}`;
      container.appendChild(heading);

      const partnerNames = new Map(
        partner.rankings.map((e, i) => [e.name, { position: i + 1, rating: e.rating }]),
      );

      // Find overlapping names
      const overlaps = [];
      for (const [name, myInfo] of myNames) {
        const theirInfo = partnerNames.get(name);
        if (theirInfo) {
          overlaps.push({
            name,
            myPos: myInfo.position,
            theirPos: theirInfo.position,
            avgPos: (myInfo.position + theirInfo.position) / 2,
            myRating: myInfo.rating,
            theirRating: theirInfo.rating,
          });
        }
      }

      overlaps.sort((a, b) => a.avgPos - b.avgPos);

      if (!overlaps.length) {
        const empty = document.createElement("p");
        empty.className = "elo-compare-empty";
        empty.textContent = "No overlapping names in your top rankings yet. Keep battling!";
        container.appendChild(empty);
        continue;
      }

      const matchLabel = document.createElement("p");
      matchLabel.className = "elo-compare-count";
      matchLabel.textContent = `${overlaps.length} names in common`;
      container.appendChild(matchLabel);

      for (const o of overlaps) {
        const row = document.createElement("div");
        row.className = "elo-compare-row";
        const isTop5 = o.myPos <= 5 && o.theirPos <= 5;
        if (isTop5) row.classList.add("elo-compare-hot");

        row.innerHTML =
          `<span class="elo-compare-name">${isTop5 ? "🔥 " : ""}${o.name}</span>` +
          `<span class="elo-compare-pos">You: #${o.myPos} (${o.myRating})</span>` +
          `<span class="elo-compare-pos">${partner.name}: #${o.theirPos} (${o.theirRating})</span>`;
        container.appendChild(row);
      }
    }
  }

  // ---------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", () => {
    init();
    detectPartnerFromHash();
  });

  return { openElo, closeElo };
})();
