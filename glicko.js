// Baby Names - Glicko-2 Battle Mode
// Head-to-head name comparisons with Glicko-2 rating system,
// confidence intervals, veto list, origin filtering, scope selection,
// server-side persistence, and partner comparison.
//
// Glicko-2 reference: https://www.glicko.net/glicko/glicko2.pdf

const glicko = (() => {
  "use strict";

  // ---------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------

  const INITIAL_RATING = 1500;
  const INITIAL_RD = 350; // Rating Deviation — high = uncertain
  const INITIAL_VOL = 0.06; // Volatility — consistency of performance
  const TAU = 0.5; // System constant — constrains volatility change
  const CONVERGENCE_RD = 80; // RD below this = "settled"
  const CONVERGENCE_THRESHOLD = 0.85; // 85% of top-20 settled = converged
  const SAVE_DEBOUNCE_MS = 2000;
  const API_BASE = "/api";

  // Glicko-2 scaling constants
  const GLICKO2_SCALE = 173.7178; // q = ln(10)/400 → scale = 1/q

  // ---------------------------------------------------------------
  // Mutable state
  // ---------------------------------------------------------------

  let fullDeck = []; // All names from grid (pre-filter)
  let pool = []; // Names eligible for battle (filtered by vetoes + origins + scope)
  let ratings = {}; // rank -> { mu, phi, sigma, wins, losses, comparisons, name }
  let vetoes = {}; // name (lowercase) -> true
  let history = []; // { winner: rank, loser: rank, timestamp }
  let totalComparisons = 0;
  let currentPair = null;
  let voterName = "";
  let partnerData = []; // [{ name, rankings }]
  let scopeLimit = 250; // Default: top 250
  let activeOrigins = []; // e.g., ["english", "celtic", "biblical"]
  let saveTimer = null;
  let serverAvailable = true;

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------

  const $ = (id) => document.getElementById(id);

  const getGender = () =>
    typeof getCurrentGender === "function" ? getCurrentGender() : "M";

  // ---------------------------------------------------------------
  // Glicko-2 math
  // ---------------------------------------------------------------

  // Convert between Glicko-1 and Glicko-2 scales
  function toGlicko2(rating, rd) {
    return {
      mu: (rating - 1500) / GLICKO2_SCALE,
      phi: rd / GLICKO2_SCALE,
    };
  }

  function fromGlicko2(mu, phi) {
    return {
      rating: Math.round(mu * GLICKO2_SCALE + 1500),
      rd: Math.round(phi * GLICKO2_SCALE),
    };
  }

  // g(φ) function
  function gFunc(phi) {
    return 1 / Math.sqrt(1 + 3 * phi * phi / (Math.PI * Math.PI));
  }

  // E(μ, μj, φj) — expected score
  function eFunc(mu, muJ, phiJ) {
    return 1 / (1 + Math.exp(-gFunc(phiJ) * (mu - muJ)));
  }

  // Update a single player's rating after one match
  function glicko2Update(player, opponent, score) {
    // score: 1 = win, 0 = loss

    // Step 1: Convert to Glicko-2 scale
    const p = toGlicko2(player.mu, player.phi);
    const o = toGlicko2(opponent.mu, opponent.phi);

    // Step 2: Compute variance v
    const gPhi = gFunc(o.phi);
    const eMu = eFunc(p.mu, o.mu, o.phi);
    const v = 1 / (gPhi * gPhi * eMu * (1 - eMu));

    // Step 3: Compute estimated improvement delta
    const delta = v * gPhi * (score - eMu);

    // Step 4: Determine new volatility (simplified Illinois algorithm)
    const a = Math.log(player.sigma * player.sigma);
    const epsilon = 0.000001;
    const phi2 = p.phi * p.phi;
    const delta2 = delta * delta;

    function f(x) {
      const ex = Math.exp(x);
      const d2v = delta2 - phi2 - v - ex;
      const term1 = (ex * d2v) / (2 * (phi2 + v + ex) * (phi2 + v + ex));
      const term2 = (x - a) / (TAU * TAU);
      return term1 - term2;
    }

    // Bisection to find new volatility
    let A = a;
    let B;
    if (delta2 > phi2 + v) {
      B = Math.log(delta2 - phi2 - v);
    } else {
      let k = 1;
      while (f(a - k * TAU) < 0) k++;
      B = a - k * TAU;
    }

    let fA = f(A);
    let fB = f(B);
    while (Math.abs(B - A) > epsilon) {
      const C = A + (A - B) * fA / (fB - fA);
      const fC = f(C);
      if (fC * fB <= 0) {
        A = B;
        fA = fB;
      } else {
        fA = fA / 2;
      }
      B = C;
      fB = fC;
    }

    const newSigma = Math.exp(A / 2);

    // Step 5: Update rating deviation
    const phiStar = Math.sqrt(phi2 + newSigma * newSigma);

    // Step 6: Update rating and RD
    const newPhi = 1 / Math.sqrt(1 / (phiStar * phiStar) + 1 / v);
    const newMu = p.mu + newPhi * newPhi * gPhi * (score - eMu);

    // Convert back to Glicko-1 scale
    const result = fromGlicko2(newMu, newPhi);
    return {
      mu: result.rating,
      phi: result.rd,
      sigma: newSigma,
    };
  }

  function updateRatings(winnerRank, loserRank) {
    const w = ratings[winnerRank];
    const l = ratings[loserRank];
    if (!w || !l) return;

    const newW = glicko2Update(w, l, 1);
    const newL = glicko2Update(l, w, 0);

    w.mu = newW.mu;
    w.phi = newW.phi;
    w.sigma = newW.sigma;
    w.wins++;
    w.comparisons++;

    l.mu = newL.mu;
    l.phi = newL.phi;
    l.sigma = newL.sigma;
    l.losses++;
    l.comparisons++;
  }

  // ---------------------------------------------------------------
  // Pair selection — weighted by RD (explore uncertain names)
  // ---------------------------------------------------------------

  function pickPair() {
    if (pool.length < 2) return null;

    // Weight by RD — high RD names need more comparisons
    const weighted = pool.map((row) => {
      const r = ratings[row.rank];
      const rd = r ? r.phi : INITIAL_RD;
      return { row, weight: rd };
    });

    const totalWeight = weighted.reduce((s, w) => s + w.weight, 0);
    const pick1 = pickWeighted(weighted, totalWeight);

    // Pick opponent with similar rating for informative matchup
    const r1 = (ratings[pick1.rank] || {}).mu || INITIAL_RATING;
    const candidates = weighted.filter((w) => w.row.rank !== pick1.rank);

    candidates.sort((a, b) => {
      const ra = (ratings[a.row.rank] || {}).mu || INITIAL_RATING;
      const rb = (ratings[b.row.rank] || {}).mu || INITIAL_RATING;
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
  // Leaderboard & convergence
  // ---------------------------------------------------------------

  function getLeaderboard(n = 20) {
    return Object.entries(ratings)
      .map(([rank, data]) => ({ rank: Number(rank), ...data }))
      .filter((e) => e.comparisons > 0)
      .sort((a, b) => b.mu - a.mu)
      .slice(0, n);
  }

  function getConvergenceInfo() {
    const top = getLeaderboard(20);
    if (top.length < 5) return { converged: false, pct: 0, stable: 0, total: top.length };
    const stable = top.filter((e) => e.phi <= CONVERGENCE_RD).length;
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
    debounceSave();
  }

  function removeVeto(name) {
    delete vetoes[name.toLowerCase()];
    rebuildPool();
    debounceSave();
  }

  function isVetoed(row) {
    const name = row.name.toLowerCase();
    if (vetoes[name]) return true;
    if (row.spelling_variants) {
      for (const v of row.spelling_variants.split(" ")) {
        if (v && vetoes[v.toLowerCase()]) return true;
      }
    }
    return false;
  }

  // ---------------------------------------------------------------
  // Pool building — scope + origins + vetoes
  // ---------------------------------------------------------------

  function rebuildPool() {
    fullDeck = typeof getSwipeDeck === "function" ? getSwipeDeck() : [];

    let filtered = fullDeck;

    // Apply scope limit (top N by rank, or exclude top N if negative)
    if (scopeLimit < 0) {
      filtered = filtered.slice(Math.abs(scopeLimit));
    } else if (scopeLimit > 0 && scopeLimit < filtered.length) {
      filtered = filtered.slice(0, scopeLimit);
    }

    // Apply origin filter
    if (activeOrigins.length > 0) {
      filtered = filtered.filter((row) => {
        if (!row.origin) return false;
        const origins = row.origin.split("|");
        return activeOrigins.some((o) => origins.includes(o));
      });
    }

    // Apply vetoes
    pool = filtered.filter((row) => !isVetoed(row));
  }

  // ---------------------------------------------------------------
  // Persistence — server + localStorage fallback
  // ---------------------------------------------------------------

  function getState() {
    return {
      user: voterName,
      gender: getGender(),
      ratings,
      vetoes,
      history: history.slice(-500),
      totalComparisons,
      scopeLimit,
      activeOrigins,
      shortlist,
    };
  }

  function applyState(data) {
    ratings = data.ratings || {};
    vetoes = data.vetoes || {};
    history = data.history || [];
    totalComparisons = data.totalComparisons || 0;
    scopeLimit = data.scopeLimit || 250;
    activeOrigins = data.activeOrigins || [];
    shortlist = data.shortlist || {};
  }

  function debounceSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => saveState(), SAVE_DEBOUNCE_MS);
  }

  async function saveState() {
    const state = getState();

    // Always save to localStorage as fallback
    const lsKey = `bn_glicko_${getGender()}`;
    try {
      localStorage.setItem(lsKey, JSON.stringify(state));
    } catch { /* storage full */ }

    // Save to server if user has a name
    if (!voterName) return;
    try {
      const res = await fetch(`${API_BASE}/state`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });
      serverAvailable = res.ok;
    } catch {
      serverAvailable = false;
    }
  }

  async function loadState() {
    // Try server first if user has a name
    if (voterName) {
      try {
        const res = await fetch(
          `${API_BASE}/state?user=${encodeURIComponent(voterName)}&gender=${getGender()}`
        );
        if (res.ok) {
          const data = await res.json();
          applyState(data);
          serverAvailable = true;
          return;
        }
      } catch {
        serverAvailable = false;
      }
    }

    // Fall back to localStorage
    const lsKey = `bn_glicko_${getGender()}`;
    try {
      const raw = localStorage.getItem(lsKey);
      if (raw) applyState(JSON.parse(raw));
    } catch { /* corrupted */ }
  }

  // ---------------------------------------------------------------
  // Screens
  // ---------------------------------------------------------------

  const SCREENS = ["elo-intro", "elo-battle", "elo-results", "elo-victory"];
  let shortlist = {}; // rank -> true (starred names)

  function showScreen(id) {
    for (const s of SCREENS) $(s).style.display = s === id ? "" : "none";
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------

  function init() {
    $("elo-launch").addEventListener("click", openGlicko);
    $("elo-close").addEventListener("click", closeGlicko);
    $("elo-start-btn").addEventListener("click", startBattling);
    $("elo-start-fresh").addEventListener("click", startFresh);
    $("elo-left-card").addEventListener("click", (e) => {
      if (e.target.closest(".elo-fighter-veto")) return;
      pickWinner("left");
    });
    $("elo-right-card").addEventListener("click", (e) => {
      if (e.target.closest(".elo-fighter-veto")) return;
      pickWinner("right");
    });
    $("elo-skip-btn").addEventListener("click", skipPair);
    $("elo-leaderboard-btn").addEventListener("click", showResults);
    $("elo-results-close").addEventListener("click", () => {
      showScreen("elo-battle");
      nextBattle();
    });
    $("elo-results-done").addEventListener("click", closeGlicko);

    // Victory screen
    const victoryShare = $("elo-victory-share");
    if (victoryShare) victoryShare.addEventListener("click", shareRankings);
    const victoryBack = $("elo-victory-back");
    if (victoryBack) victoryBack.addEventListener("click", () => {
      showScreen("elo-battle");
      nextBattle();
    });

    // Veto buttons on battle cards
    $("elo-left-veto").addEventListener("click", (e) => {
      e.stopPropagation();
      if (currentPair) { addVeto(currentPair.left.name); nextBattle(); }
    });
    $("elo-right-veto").addEventListener("click", (e) => {
      e.stopPropagation();
      if (currentPair) { addVeto(currentPair.right.name); nextBattle(); }
    });

    // Veto input
    $("elo-veto-add-btn").addEventListener("click", addVetoFromInput);
    $("elo-veto-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addVetoFromInput();
    });

    // Keyboard
    document.addEventListener("keydown", (e) => {
      if ($("elo-overlay").style.display === "none") return;
      if ($("elo-battle").style.display === "none") return;
      if (e.target.tagName === "INPUT") return;
      if (e.key === "ArrowLeft") { e.preventDefault(); pickWinner("left"); }
      else if (e.key === "ArrowRight") { e.preventDefault(); pickWinner("right"); }
      else if (e.key === "ArrowDown" || e.key === "s") { e.preventDefault(); skipPair(); }
    });

    // User name — load state on change
    $("elo-voter-name").addEventListener("change", async function () {
      voterName = this.value.trim();
      if (voterName) {
        await loadState();
        rebuildPool();
        showIntro();
      }
    });

    // Sharing
    $("elo-share-btn").addEventListener("click", shareRankings);
    $("elo-add-partner-btn").addEventListener("click", () => {
      const row = $("elo-partner-input-row");
      row.style.display = row.style.display === "none" ? "" : "none";
      $("elo-partner-url").value = "";
      $("elo-partner-url").focus();
    });
    $("elo-partner-go").addEventListener("click", loadPartnerComparison);
    $("elo-partner-url").addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadPartnerComparison();
    });

    // Accordion toggles
    document.querySelectorAll(".elo-accordion-header").forEach((header) => {
      header.addEventListener("click", function () {
        const acc = this.closest(".elo-accordion");
        // Close others
        document.querySelectorAll(".elo-accordion.open").forEach((a) => {
          if (a !== acc) a.classList.remove("open");
        });
        acc.classList.toggle("open");
      });
    });

    // Scope pills
    document.querySelectorAll(".elo-scope-pill").forEach((pill) => {
      pill.addEventListener("click", function () {
        document.querySelectorAll(".elo-scope-pill").forEach((p) => p.classList.remove("active"));
        this.classList.add("active");
        scopeLimit = Number(this.dataset.scope) || 0;
        $("elo-acc-scope-val").textContent = this.textContent;
        rebuildPool();
        updatePoolInfo();
        debounceSave();
      });
    });

    // Gender pills
    document.querySelectorAll(".elo-gender-pill").forEach((pill) => {
      pill.addEventListener("click", function () {
        document.querySelectorAll(".elo-gender-pill").forEach((p) => p.classList.remove("active"));
        this.classList.add("active");
        $("elo-acc-gender-val").textContent = this.textContent;
        // Trigger gender switch in grid.js
        const genderBtn = document.querySelector(`.gender-btn[data-gender="${this.dataset.gender}"]`);
        if (genderBtn) genderBtn.click();
        rebuildPool();
        updatePoolInfo();
      });
    });

    // Origin chips
    document.querySelectorAll(".elo-origin-chip").forEach((chip) => {
      chip.addEventListener("click", function () {
        const origin = this.dataset.origin;
        const idx = activeOrigins.indexOf(origin);
        if (idx !== -1) {
          activeOrigins.splice(idx, 1);
          this.classList.remove("active");
        } else {
          activeOrigins.push(origin);
          this.classList.add("active");
        }
        const val = activeOrigins.length ? activeOrigins.map((o) => o[0].toUpperCase() + o.slice(1)).join(", ") : "All";
        $("elo-acc-origins-val").textContent = val;
        rebuildPool();
        updatePoolInfo();
        debounceSave();
      });
    });
  }

  // ---------------------------------------------------------------
  // Open / Close
  // ---------------------------------------------------------------

  async function openGlicko() {
    await loadState();
    rebuildPool();

    // Ensure all pool names have ratings
    for (const row of pool) {
      if (!ratings[row.rank]) {
        ratings[row.rank] = {
          mu: INITIAL_RATING,
          phi: INITIAL_RD,
          sigma: INITIAL_VOL,
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

  function closeGlicko() {
    clearTimeout(saveTimer);
    saveState(); // Final save
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

    // Restore scope selector
    const scopeEl = $("elo-scope-select");
    if (scopeEl) scopeEl.value = String(scopeLimit || 0);

    // Restore origin chips
    document.querySelectorAll(".elo-origin-chip").forEach((chip) => {
      chip.classList.toggle("active", activeOrigins.includes(chip.dataset.origin));
    });

    updatePoolInfo();

    // Resume info
    if (totalComparisons > 0) {
      const top3 = getLeaderboard(3);
      const topNames = top3.map((e) => `${e.name} (${e.mu}±${e.phi})`).join(", ");
      $("elo-resume-info").textContent =
        `${totalComparisons} battles · Top: ${topNames}`;
      $("elo-resume-info").style.display = "";
      $("elo-start-fresh").style.display = "";
    } else {
      $("elo-resume-info").style.display = "none";
      $("elo-start-fresh").style.display = "none";
    }

    // Server status
    const statusEl = $("elo-server-status");
    if (statusEl) {
      if (!voterName) {
        statusEl.textContent = "Enter your name to sync across devices";
        statusEl.className = "elo-server-status";
      } else if (serverAvailable) {
        statusEl.textContent = "Synced to server";
        statusEl.className = "elo-server-status synced";
      } else {
        statusEl.textContent = "Offline — saving locally";
        statusEl.className = "elo-server-status offline";
      }
    }

    renderVetoList();
  }

  function updatePoolInfo() {
    $("elo-pool-size").textContent = pool.length.toLocaleString();
  }

  function renderVetoList() {
    const container = $("elo-veto-list");
    container.innerHTML = "";
    const names = Object.keys(vetoes).sort();
    const valEl = $("elo-acc-vetoes-val");
    if (valEl) valEl.textContent = names.length ? `${names.length} name${names.length > 1 ? "s" : ""}` : "0 names";
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
        updatePoolInfo();
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
    updatePoolInfo();
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
        mu: INITIAL_RATING,
        phi: INITIAL_RD,
        sigma: INITIAL_VOL,
        wins: 0,
        losses: 0,
        comparisons: 0,
        name: row.name,
      };
    }
    debounceSave();
    startBattling();
  }

  function startBattling() {
    const nameInput = $("elo-voter-name");
    if (nameInput && nameInput.value.trim()) {
      voterName = nameInput.value.trim();
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
    $("elo-left-meaning").textContent = (left.meaning || "").slice(0, 60);
    $("elo-left-stats").textContent = buildStats(left);
    renderOriginTags($("elo-left-origins"), left);

    // Right card
    $("elo-right-name").textContent = right.name;
    $("elo-right-meaning").textContent = (right.meaning || "").slice(0, 60);
    $("elo-right-stats").textContent = buildStats(right);
    renderOriginTags($("elo-right-origins"), right);

    // Progress
    $("elo-comparison-count").textContent = totalComparisons.toLocaleString();

    // Convergence
    const conv = getConvergenceInfo();
    const convEl = $("elo-convergence");
    if (totalComparisons >= 20) {
      convEl.style.display = "";
      convEl.textContent = conv.converged
        ? "Converged! Top names are stable."
        : `Stability: ${conv.pct}% (${conv.stable}/${conv.total} settled)`;
      convEl.className = `elo-convergence ${conv.converged ? "converged" : ""}`;
    } else {
      convEl.style.display = "none";
    }

    // Top 3 preview
    const top3 = getLeaderboard(3);
    $("elo-top-preview").textContent = top3.length
      ? `Leading: ${top3.map((e) => `${e.name} (${e.mu}±${e.phi})`).join(" · ")}`
      : "";

    // Animate
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
    if (row.total_count) parts.push(Number(row.total_count).toLocaleString());
    if (row.year_peak) parts.push(`peak ${row.year_peak}`);
    if (row.syllables) parts.push(`${row.syllables} syl`);
    if (row.origin) parts.push(row.origin.replace(/\|/g, ", "));
    return parts.join(" · ");
  }

  function renderOriginTags(container, row) {
    container.innerHTML = "";
    const origins = (row.origin || "").split("|").filter(Boolean);
    for (const o of origins) {
      const tag = document.createElement("span");
      tag.className = "elo-fighter-origin-tag";
      tag.textContent = o;
      container.appendChild(tag);
    }
  }

  function pickWinner(side) {
    if (!currentPair) return;
    const winner = side === "left" ? currentPair.left : currentPair.right;
    const loser = side === "left" ? currentPair.right : currentPair.left;

    updateRatings(winner.rank, loser.rank);
    totalComparisons++;
    history.push({ winner: winner.rank, loser: loser.rank, timestamp: Date.now() });

    // Flash
    const winCard = $(side === "left" ? "elo-left-card" : "elo-right-card");
    const loseCard = $(side === "left" ? "elo-right-card" : "elo-left-card");
    winCard.classList.add("elo-card-win");
    loseCard.classList.add("elo-card-lose");
    setTimeout(() => {
      winCard.classList.remove("elo-card-win");
      loseCard.classList.remove("elo-card-lose");
    }, 300);

    debounceSave();
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

    const conv = getConvergenceInfo();
    $("elo-results-stats").textContent =
      `${totalComparisons} battles · ${pool.length.toLocaleString()} names in pool · Stability: ${conv.pct}%`;

    for (let i = 0; i < board.length; i++) {
      const entry = board[i];
      const nameData = pool.find((r) => r.rank === entry.rank) || {};
      const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}.`;
      const confPct = Math.max(0, Math.min(100, ((INITIAL_RD - entry.phi) / (INITIAL_RD - 30)) * 100));
      const starred = !!shortlist[entry.rank];

      // Main row
      const row = document.createElement("div");
      row.className = `elo-lb-row${i < 3 ? " elo-lb-top3" : ""}`;
      row.innerHTML =
        `<span class="elo-lb-rank">${medal}</span>` +
        `<div class="elo-lb-main"><div class="elo-lb-name">${entry.name}</div>` +
        `<div class="elo-lb-meaning">${((nameData.meaning || "").slice(0, 50))}${nameData.origin ? " · " + nameData.origin.replace(/\|/g, ", ") : ""}</div></div>` +
        `<div class="elo-lb-conf"><div class="elo-lb-conf-fill" style="width:${confPct}%"></div></div>` +
        `<span class="elo-lb-star${starred ? " active" : ""}" data-rank="${entry.rank}">⭐</span>`;

      // Detail row (hidden by default)
      const detail = document.createElement("div");
      detail.className = "elo-lb-detail";
      detail.innerHTML =
        `<div class="elo-lb-detail-grid">` +
        `<div><span class="elo-lb-detail-label">Rating</span> ${entry.mu} ± ${entry.phi}</div>` +
        `<div><span class="elo-lb-detail-label">Record</span> ${entry.wins}W ${entry.losses}L</div>` +
        `<div><span class="elo-lb-detail-label">Rank</span> #${entry.rank}</div>` +
        `<div><span class="elo-lb-detail-label">Peak</span> ${nameData.year_peak || "—"}</div>` +
        `<div><span class="elo-lb-detail-label">Syllables</span> ${nameData.syllables || "—"}</div>` +
        `<div><span class="elo-lb-detail-label">Origin</span> ${(nameData.detailed_origin || nameData.origin || "—").replace(/\|/g, ", ")}</div>` +
        `<div><span class="elo-lb-detail-label">Meaning</span> ${(nameData.meaning || "—").slice(0, 100)}</div>` +
        `<div><span class="elo-lb-detail-label">Nicknames</span> ${nameData.nicknames || "—"}</div>` +
        `</div>`;

      // Toggle detail on row click
      row.addEventListener("click", (e) => {
        if (e.target.closest(".elo-lb-star")) return;
        detail.classList.toggle("open");
      });

      // Star toggle
      row.querySelector(".elo-lb-star").addEventListener("click", (e) => {
        e.stopPropagation();
        const rank = Number(e.target.dataset.rank);
        if (shortlist[rank]) {
          delete shortlist[rank];
          e.target.classList.remove("active");
        } else {
          shortlist[rank] = true;
          e.target.classList.add("active");
        }
        debounceSave();
      });

      container.appendChild(row);
      container.appendChild(detail);
    }

    // Check for convergence → victory screen
    const conv2 = getConvergenceInfo();
    if (conv2.converged && totalComparisons >= 50) {
      showVictory();
      return;
    }

    renderComparison();
  }

  // ---------------------------------------------------------------
  // Victory screen
  // ---------------------------------------------------------------

  function showVictory() {
    showScreen("elo-victory");
    const top = getLeaderboard(5);
    const container = $("elo-victory-shortlist");
    container.innerHTML = "";
    for (const entry of top) {
      const pill = document.createElement("span");
      pill.className = "elo-shortlist-name";
      pill.textContent = entry.name;
      container.appendChild(pill);
    }
    // Fire confetti if available
    if (typeof confetti === "function") {
      confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
      setTimeout(() => confetti({ particleCount: 50, spread: 100, origin: { y: 0.5 } }), 300);
    }
  }

  // ---------------------------------------------------------------
  // Sharing & Comparison
  // ---------------------------------------------------------------

  function safeEncode(str) {
    return btoa(Array.from(new TextEncoder().encode(str), (b) => String.fromCharCode(b)).join(""));
  }

  function safeDecode(str) {
    return new TextDecoder().decode(Uint8Array.from(atob(str), (c) => c.charCodeAt(0)));
  }

  function shareRankings() {
    if (!voterName) {
      const name = prompt("Enter your name:");
      if (!name) return;
      voterName = name.trim();
      debounceSave();
      $("elo-voter-name").value = voterName;
    }
    const top = getLeaderboard(30);
    if (!top.length) { alert("No rankings yet!"); return; }

    const encoded = safeEncode(JSON.stringify({
      n: voterName,
      g: getGender(),
      t: top.map((e) => ({ r: e.rank, n: e.name, s: e.mu, d: e.phi })),
    }));
    const url = `${location.origin}${location.pathname}#elo=${encoded}`;

    if (navigator.share) {
      navigator.share({ title: `${voterName}'s rankings`, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(
        () => showToast("Link copied!"),
        () => prompt("Copy this link:", url),
      );
    }
  }

  async function loadPartnerComparison() {
    const input = $("elo-partner-url").value.trim();
    if (!input) return;

    // If it looks like a name (no URL characters), try server lookup
    if (!input.includes("#") && !input.includes("/")) {
      try {
        const res = await fetch(
          `${API_BASE}/compare?a=${encodeURIComponent(voterName)}&b=${encodeURIComponent(input)}&gender=${getGender()}`
        );
        if (res.ok) {
          const data = await res.json();
          partnerData = [{
            name: input,
            rankings: data.b.map((e, i) => ({
              rank: e.rank,
              name: e.name,
              rating: e.mu,
              rd: e.phi,
              position: i + 1,
            })),
          }];
          $("elo-partner-input-row").style.display = "none";
          showToast(`Loaded ${input}'s rankings`);
          showResults();
          return;
        }
      } catch { /* fall through to URL decode */ }
    }

    // Try URL decode
    try {
      const hashPart = input.includes("#") ? input.split("#")[1] : input;
      const encoded = hashPart.startsWith("elo=") ? hashPart.slice(4) : hashPart;
      const data = JSON.parse(safeDecode(encoded));
      if (!data || !data.t) throw new Error("bad");

      partnerData = [{
        name: data.n || "Partner",
        rankings: data.t.map((e, i) => ({
          rank: e.r, name: e.n, rating: e.s, rd: e.d || 100, position: i + 1,
        })),
      }];
      $("elo-partner-input-row").style.display = "none";
      showToast(`Loaded ${data.n || "Partner"}'s rankings`);
      showResults();
    } catch {
      alert("Could not load. Enter a name or paste a link.");
    }
  }

  function renderComparison() {
    const container = $("elo-compare-results");
    container.innerHTML = "";

    if (!partnerData.length) {
      $("elo-compare-section").style.display = "none";
      return;
    }
    $("elo-compare-section").style.display = "";

    const myTop = getLeaderboard(20);
    const myMap = new Map(myTop.map((e, i) => [e.name, { pos: i + 1, mu: e.mu, phi: e.phi }]));

    for (const partner of partnerData) {
      const partnerMap = new Map(
        partner.rankings.slice(0, 20).map((e, i) => [e.name, { pos: i + 1, mu: e.rating, phi: e.rd }])
      );

      // --- Section 1: Overlap ---
      const overlaps = [];
      for (const [name, my] of myMap) {
        const theirs = partnerMap.get(name);
        if (theirs) {
          overlaps.push({
            name, myPos: my.pos, theirPos: theirs.pos,
            avgPos: (my.pos + theirs.pos) / 2,
            myMu: my.mu, theirMu: theirs.mu,
            myPhi: my.phi, theirPhi: theirs.phi,
            combinedMu: Math.round((my.mu + theirs.mu) / 2),
            combinedConf: my.phi <= CONVERGENCE_RD && theirs.phi <= CONVERGENCE_RD ? "high" :
              my.phi <= CONVERGENCE_RD || theirs.phi <= CONVERGENCE_RD ? "medium" : "low",
          });
        }
      }
      overlaps.sort((a, b) => a.avgPos - b.avgPos);

      // Overlap header
      const overlapH = document.createElement("h4");
      overlapH.textContent = `🔥 Names you both love (${overlaps.length})`;
      container.appendChild(overlapH);

      if (overlaps.length) {
        for (const o of overlaps) {
          const hot = o.myPos <= 5 && o.theirPos <= 5;
          const card = document.createElement("div");
          card.className = `elo-overlap-card${hot ? " hot" : ""}`;

          const confLabel = o.combinedConf === "high" ? "High confidence — you both love this one" :
            o.combinedConf === "medium" ? "Growing confidence — keep battling" : "Still exploring — needs more battles";

          card.innerHTML =
            `<span class="elo-overlap-fire">${hot ? "🔥" : "💛"}</span>` +
            `<div class="elo-overlap-info">` +
            `<div class="elo-overlap-name">${o.name}</div>` +
            `<div class="elo-overlap-conf">${confLabel}</div>` +
            `<div class="elo-overlap-pos">You: #${o.myPos} (${o.myMu}) · ${partner.name}: #${o.theirPos} (${o.theirMu})</div>` +
            `</div>`;
          container.appendChild(card);
        }
      } else {
        const empty = document.createElement("p");
        empty.className = "elo-compare-empty";
        empty.textContent = "No overlap yet. Keep battling!";
        container.appendChild(empty);
      }

      // --- Section 2: Side by side ---
      const sideH = document.createElement("h4");
      sideH.style.marginTop = "1.5rem";
      sideH.textContent = "📊 Side by Side";
      container.appendChild(sideH);

      const grid = document.createElement("div");
      grid.className = "elo-sbs-grid";

      // Headers
      grid.innerHTML =
        `<div class="elo-sbs-header">You</div>` +
        `<div class="elo-sbs-header">${partner.name}</div>`;

      const overlapNames = new Set(overlaps.map((o) => o.name));
      const maxRows = Math.max(myTop.length, partner.rankings.slice(0, 20).length);

      for (let i = 0; i < maxRows; i++) {
        const myEntry = myTop[i];
        const theirEntry = partner.rankings[i];

        const myCell = document.createElement("div");
        myCell.className = "elo-sbs-cell";
        if (myEntry) {
          const isOverlap = overlapNames.has(myEntry.name);
          myCell.innerHTML = `<span class="${isOverlap ? "elo-sbs-match" : ""}">${i + 1}. ${myEntry.name} <small>${myEntry.mu}±${myEntry.phi}</small></span>`;
        }

        const theirCell = document.createElement("div");
        theirCell.className = "elo-sbs-cell";
        if (theirEntry) {
          const isOverlap = overlapNames.has(theirEntry.name);
          theirCell.innerHTML = `<span class="${isOverlap ? "elo-sbs-match" : ""}">${i + 1}. ${theirEntry.name} <small>${theirEntry.rating}±${theirEntry.rd}</small></span>`;
        }

        grid.appendChild(myCell);
        grid.appendChild(theirCell);
      }

      container.appendChild(grid);
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

  // ---------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", init);

  return { openGlicko, closeGlicko };
})();
