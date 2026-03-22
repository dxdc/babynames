// Baby Names - Swipe Mode
// Tinder-style name swiping with multi-person sharing and comparison
//
// Sharing model: everyone is a peer. Anyone can:
//  1. Share their picks (generates a URL with name + liked/maybe ranks)
//  2. Load anyone else's picks (paste their URL, keyed by name — re-pasting updates)
//  3. Share the deck (frozen filter state so everyone swipes the same list)
//  4. Export/import JSON for backup across browsers/devices
//
// Picks URLs always reflect current state, so re-sharing gives updated picks.

const swipe = (() => {
  "use strict";

  // ---------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------

  const SECS_PER_CARD = 4;
  const STORAGE_PREFIX = "bn_swipe_";

  // ---------------------------------------------------------------
  // Mutable state
  // ---------------------------------------------------------------

  let deck = []; // full filtered list from table
  let activeDeck = []; // deck sliced to scope limit (what we actually swipe)
  let deckHash = "";
  let currentIndex = 0;
  let liked = {}; // rank -> { name, spellings: [] }
  let maybe = {}; // rank -> { name, spellings: [] }
  let passed = {}; // rank -> true
  let actionHistory = [];
  let voterName = "";
  let otherVoters = [];
  let sessionId = "";
  let scopeLimit = 0; // 0 = all
  let pendingPicks = false; // set true when a #picks= URL is detected at boot

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------

  const $ = (id) => document.getElementById(id);

  function hashStr(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
      h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return Math.abs(h).toString(36).slice(0, 6);
  }

  const buildDeckHash = (rows) =>
    hashStr(rows.map((r) => `${r.rank}:${r.name}`).join(","));

  function formatTime(count) {
    const mins = Math.ceil((count * SECS_PER_CARD) / 60);
    if (mins < 2) return "~1 min";
    if (mins < 60) return `~${mins} min`;
    return `~${(mins / 60).toFixed(1)} hrs`;
  }

  // Count only reviews that are within the active deck scope
  const reviewedCount = () => {
    if (!activeDeck.length) {
      return (
        Object.keys(liked).length +
        Object.keys(maybe).length +
        Object.keys(passed).length
      );
    }
    const activeRanks = new Set(activeDeck.map((d) => d.rank));
    let count = 0;
    for (const r of Object.keys(liked)) if (activeRanks.has(Number(r))) count++;
    for (const r of Object.keys(maybe)) if (activeRanks.has(Number(r))) count++;
    for (const r of Object.keys(passed))
      if (activeRanks.has(Number(r))) count++;
    return count;
  };

  const isReviewed = (rank) => !!liked[rank] || !!maybe[rank] || !!passed[rank];

  const getGender = () =>
    typeof getCurrentGender === "function" ? getCurrentGender() : "M";

  // ---------------------------------------------------------------
  // Encode / decode for sharing
  // ---------------------------------------------------------------

  function encodeSession() {
    return btoa(
      JSON.stringify({
        v: deckHash,
        g: getGender(),
        ranks: deck.map((d) => d.rank),
      }),
    );
  }

  function encodePicks() {
    return btoa(
      JSON.stringify({
        v: deckHash,
        n: voterName,
        g: getGender(),
        l: Object.keys(liked).map(Number),
        m: Object.keys(maybe).map(Number),
      }),
    );
  }

  function decodePicks(encoded) {
    try {
      return JSON.parse(atob(encoded));
    } catch {
      return null;
    }
  }

  // ---------------------------------------------------------------
  // Screen management
  // ---------------------------------------------------------------

  const SCREENS = [
    "swipe-intro",
    "swipe-cards",
    "swipe-complete",
    "swipe-results",
  ];

  function showScreen(id) {
    for (const s of SCREENS) {
      $(s).style.display = s === id ? "" : "none";
    }
  }

  // ---------------------------------------------------------------
  // DOM setup
  // ---------------------------------------------------------------

  function init() {
    $("swipe-launch").addEventListener("click", openSwipe);
    $("swipe-close").addEventListener("click", closeSwipe);
    $("swipe-start-btn").addEventListener("click", startSwiping);
    $("swipe-start-fresh").addEventListener("click", startFresh);
    $("swipe-results-btn").addEventListener("click", showResults);

    $("swipe-pass").addEventListener("click", () => act("pass"));
    $("swipe-maybe").addEventListener("click", () => act("maybe"));
    $("swipe-like").addEventListener("click", () => act("like"));
    $("swipe-undo").addEventListener("click", undo);
    $("swipe-peek").addEventListener("click", showResults);

    $("complete-share-btn").addEventListener("click", sharePicks);
    $("complete-results-btn").addEventListener("click", showResults);

    $("results-close").addEventListener("click", closeSwipe);
    $("results-back").addEventListener("click", () => {
      if (currentIndex < activeDeck.length) {
        showScreen("swipe-cards");
        advanceToNext();
        renderCard();
      } else if (reviewedCount() >= activeDeck.length) {
        showScreen("swipe-complete");
      } else {
        showScreen("swipe-intro");
      }
    });

    $("share-deck-btn").addEventListener("click", shareDeck);
    $("share-picks-btn").addEventListener("click", sharePicks);
    $("export-btn").addEventListener("click", exportData);
    $("import-btn").addEventListener("click", () => $("import-file").click());
    $("import-file").addEventListener("change", importData);
    $("add-voter-btn").addEventListener("click", showAddVoter);
    $("add-voter-go").addEventListener("click", loadVoterPicks);

    $("voter-name-input").addEventListener("change", function () {
      voterName = this.value.trim();
      saveSession();
    });

    document.addEventListener("keydown", (e) => {
      if ($("swipe-overlay").style.display === "none") return;
      if (e.key === "Escape") {
        closeSwipe();
        return;
      }
      if ($("swipe-cards").style.display === "none") return;
      if (e.key === "ArrowLeft") act("pass");
      else if (e.key === "ArrowUp") act("maybe");
      else if (e.key === "ArrowRight") act("like");
      else if (e.key === "z" && (e.ctrlKey || e.metaKey)) undo();
    });

    setupGestures();
  }

  // ---------------------------------------------------------------
  // Open / close
  // ---------------------------------------------------------------

  function openSwipe() {
    deck = typeof getSwipeDeck === "function" ? getSwipeDeck() : [];
    if (!deck.length) return;

    // Save any URL-loaded voters before loadSession resets state
    const pendingVoters = [...otherVoters];

    deckHash = buildDeckHash(deck);
    sessionId = `${STORAGE_PREFIX}${getGender()}_${deckHash}`;

    loadSession();

    // Merge URL-loaded voters (keyed by name, URL wins over stale session data)
    for (const pv of pendingVoters) {
      otherVoters = otherVoters.filter((v) => v.name !== pv.name);
      otherVoters.push(pv);
    }
    if (pendingVoters.length) saveSession();

    $("swipe-overlay").style.display = "";
    showIntro();
    document.body.style.overflow = "hidden";
  }

  function closeSwipe() {
    $("swipe-overlay").style.display = "none";
    for (const s of SCREENS) $(s).style.display = "none";
    document.body.style.overflow = "";
  }

  // ---------------------------------------------------------------
  // Intro screen
  // ---------------------------------------------------------------

  function showIntro() {
    showScreen("swipe-intro");

    $("voter-name-input").value = voterName;

    // Build scope options based on filtered deck size
    buildScopeOptions();
    updateEstimates();

    // Resume info
    const reviewed = reviewedCount();
    const resumeEl = $("swipe-resume-info");
    const freshBtn = $("swipe-start-fresh");
    if (reviewed > 0) {
      const likedN = Object.keys(liked).length;
      const maybeN = Object.keys(maybe).length;
      const remaining = activeDeck.length - reviewed;
      resumeEl.textContent = `${reviewed.toLocaleString()} reviewed · ${likedN.toLocaleString()} liked · ${maybeN.toLocaleString()} maybe · ${remaining.toLocaleString()} remaining`;
      resumeEl.style.display = "";
      freshBtn.style.display = "";
      advanceToNext();
    } else {
      resumeEl.style.display = "none";
      freshBtn.style.display = "none";
      currentIndex = 0;
    }

    const votersNote = $("swipe-voters-note");
    if (otherVoters.length) {
      const descs = otherVoters.map((v) => {
        const n = v.name || "Someone";
        const gLabel =
          v.gender === "M" ? "boys" : v.gender === "F" ? "girls" : "";
        return gLabel ? `${n} (${gLabel})` : n;
      });
      votersNote.textContent = `${descs.join(", ")} shared picks — compare in Results`;
      votersNote.style.display = "";
    } else {
      votersNote.style.display = "none";
    }

    $("storage-warning").style.display = "";
  }

  function buildScopeOptions() {
    const container = $("scope-options");
    container.innerHTML = "";
    const total = deck.length;
    const presets = [50, 100, 250, 500, 1000, 2000, 5000].filter(
      (n) => n < total,
    );
    presets.push(total);
    // Keep at most 4 options: pick evenly spaced ones
    let options = presets;
    if (options.length > 5) {
      const keep = [presets[0]];
      const step = (presets.length - 1) / 3;
      for (let i = 1; i < 3; i++) keep.push(presets[Math.round(i * step)]);
      keep.push(presets[presets.length - 1]);
      options = [...new Set(keep)];
    }

    // Default to "all" if no scope saved, or restore saved
    if (!scopeLimit || scopeLimit > total) scopeLimit = total;

    for (const n of options) {
      const btn = document.createElement("button");
      btn.className = `scope-option${n === scopeLimit ? " active" : ""}`;
      btn.type = "button";
      const label = n === total ? "All" : `Top ${n.toLocaleString()}`;
      const time = formatTime(Math.max(0, n - reviewedCount()));
      btn.innerHTML =
        `<span class="scope-label">${label}</span>` +
        `<span class="scope-detail">${n.toLocaleString()} names · ${time}</span>`;
      btn.addEventListener("click", () => {
        scopeLimit = n;
        activeDeck = deck.slice(0, scopeLimit);
        container
          .querySelectorAll(".scope-option")
          .forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        updateEstimates();
        saveSession();
      });
      container.appendChild(btn);
    }

    activeDeck = deck.slice(0, scopeLimit);
  }

  function updateEstimates() {
    const count = activeDeck.length;
    const reviewed = reviewedCount();
    const remaining = Math.max(0, count - reviewed);
    $("swipe-deck-count").textContent = count.toLocaleString();
    $("swipe-time-est").textContent = formatTime(remaining);

    // Hint with example name at boundary
    if (activeDeck.length > 0 && activeDeck.length < deck.length) {
      const last = activeDeck[activeDeck.length - 1];
      $("scope-hint").textContent =
        `Includes names up to #${last.rank} (e.g., ${last.name})`;
    } else {
      $("scope-hint").textContent = "";
    }
  }

  function advanceToNext() {
    currentIndex = 0;
    while (
      currentIndex < activeDeck.length &&
      isReviewed(activeDeck[currentIndex].rank)
    ) {
      currentIndex++;
    }
  }

  function startFresh() {
    liked = {};
    maybe = {};
    passed = {};
    actionHistory = [];
    currentIndex = 0;
    saveSession();
    startSwiping();
  }

  function startSwiping() {
    showScreen("swipe-cards");
    advanceToNext();
    if (currentIndex >= activeDeck.length) {
      showResults();
      return;
    }
    renderCard();
  }

  // ---------------------------------------------------------------
  // Card rendering
  // ---------------------------------------------------------------

  function renderCard() {
    if (currentIndex >= activeDeck.length) {
      showComplete();
      return;
    }

    const d = activeDeck[currentIndex];
    const card = $("swipe-card");

    $("card-name").textContent = d.name;

    // Variant chips — multi-select, primary always selected
    const varEl = $("card-variants");
    varEl.innerHTML = "";
    const allSpellings = [d.name];
    if (d.spelling_variants) {
      for (const v of d.spelling_variants.split(" ")) {
        if (v) allSpellings.push(v);
      }
    }
    if (allSpellings.length > 1) {
      allSpellings.forEach((v, i) => {
        const chip = document.createElement("span");
        chip.className = `variant-chip${i === 0 ? " selected" : ""}`;
        chip.textContent = v;
        chip.dataset.spelling = v;
        chip.addEventListener("click", () => {
          // Toggle, but at least one must stay selected
          chip.classList.toggle("selected");
          const anySelected = varEl.querySelector(".variant-chip.selected");
          if (!anySelected) chip.classList.add("selected");
        });
        varEl.appendChild(chip);
      });
    }

    // Stats
    const parts = [
      `#${d.rank}`,
      `${Number(d.total_count).toLocaleString()} babies`,
      `${d.year_min}–${d.year_max}`,
      `peaked ${d.year_peak}`,
    ];
    if (d.syllables) parts.push(`${d.syllables} syl`);
    if (d.unisex_pct != null) {
      const sym = d.unisex_dominant === "M" ? "♂" : "♀";
      parts.push(`${d.unisex_pct}% unisex ${sym}`);
    }
    $("card-stats").textContent = parts.join(" · ");

    // Progress
    const total = activeDeck.length;
    const reviewed = reviewedCount();
    $("swipe-progress-bar").style.width =
      `${Math.min(100, (reviewed / total) * 100).toFixed(1)}%`;
    $("swipe-progress-text").textContent =
      `${reviewed.toLocaleString()} / ${total.toLocaleString()}`;
    $("progress-liked-count").textContent =
      `♥ ${Object.keys(liked).length.toLocaleString()}`;
    $("progress-maybe-count").textContent =
      `★ ${Object.keys(maybe).length.toLocaleString()}`;

    $("swipe-undo").style.visibility = actionHistory.length
      ? "visible"
      : "hidden";

    // Reset + entrance animation
    card.style.boxShadow = "";
    card.style.transition = "transform 0.3s ease, opacity 0.25s ease";
    card.classList.remove("card-exit-left", "card-exit-right", "card-exit-up");
    card.style.transform = "scale(0.92) translateY(20px)";
    card.style.opacity = "0.5";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        card.style.transform = "";
        card.style.opacity = "1";
      });
    });
  }

  function getSelectedSpellings() {
    const chips = $("card-variants").querySelectorAll(".variant-chip.selected");
    if (chips.length === 0) return [activeDeck[currentIndex].name];
    return Array.from(chips).map((c) => c.dataset.spelling);
  }

  // ---------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------

  let acting = false;

  function act(action) {
    if (acting || currentIndex >= activeDeck.length) return;
    acting = true;

    const d = activeDeck[currentIndex];
    const spellings = getSelectedSpellings();
    const card = $("swipe-card");
    const dir = action === "pass" ? "left" : action === "like" ? "right" : "up";

    card.classList.add(`card-exit-${dir}`);

    // Flash feedback
    const flash = $("swipe-flash");
    const flashMap = {
      like: ["green", "♥"],
      pass: ["red", "✗"],
      maybe: ["amber", "★"],
    };
    const [cls, icon] = flashMap[action];
    flash.className = `swipe-flash flash-${cls}`;
    flash.textContent = icon;
    flash.style.display = "";
    setTimeout(() => {
      flash.style.display = "none";
    }, 400);

    actionHistory.push({ rank: d.rank, action, spellings });

    if (action === "like") {
      liked[d.rank] = { name: d.name, spellings };
      delete maybe[d.rank];
      delete passed[d.rank];
    } else if (action === "maybe") {
      maybe[d.rank] = { name: d.name, spellings };
      delete liked[d.rank];
      delete passed[d.rank];
    } else {
      passed[d.rank] = true;
      delete liked[d.rank];
      delete maybe[d.rank];
    }

    saveSession();
    setTimeout(() => {
      currentIndex++;
      advanceToNext();
      renderCard();
      acting = false;
    }, 280);
  }

  function undo() {
    if (!actionHistory.length) return;
    const last = actionHistory.pop();
    delete liked[last.rank];
    delete maybe[last.rank];
    delete passed[last.rank];
    for (let i = 0; i < activeDeck.length; i++) {
      if (activeDeck[i].rank === last.rank) {
        currentIndex = i;
        break;
      }
    }
    saveSession();
    renderCard();
  }

  // ---------------------------------------------------------------
  // Completion
  // ---------------------------------------------------------------

  function showComplete() {
    showScreen("swipe-complete");

    const likedN = Object.keys(liked).length;
    const maybeN = Object.keys(maybe).length;
    $("complete-summary").textContent =
      `${likedN.toLocaleString()} liked · ${maybeN.toLocaleString()} maybe`;

    const flash = $("swipe-flash");
    flash.className = "swipe-flash flash-complete";
    flash.textContent = "🎉";
    flash.style.display = "";
    setTimeout(() => {
      flash.style.display = "none";
    }, 1200);
  }

  // ---------------------------------------------------------------
  // Results / shortlist
  // ---------------------------------------------------------------

  function showResults() {
    showScreen("swipe-results");

    $("results-liked-count").textContent =
      Object.keys(liked).length.toLocaleString();
    $("results-maybe-count").textContent =
      Object.keys(maybe).length.toLocaleString();

    renderResultList($("results-liked"), liked, "liked");
    renderResultList($("results-maybe"), maybe, "maybe");

    const banner = $("compare-banner");
    if (otherVoters.length) {
      $("compare-section").style.display = "";
      renderComparison();

      // Build banner text
      const ownPicks = Object.keys(liked).length + Object.keys(maybe).length;
      const currentGdr = getGender();
      const parts = otherVoters.map((v) => {
        const n =
          Object.keys(v.liked || {}).length + Object.keys(v.maybe || {}).length;
        const gLabel =
          v.gender === "M" ? "boys" : v.gender === "F" ? "girls" : "";
        const mismatch = v.gender && v.gender !== currentGdr;
        return (
          `<strong>${v.name || "Someone"}</strong> shared ${n.toLocaleString()} ${gLabel} pick${n !== 1 ? "s" : ""}` +
          (mismatch ? " ⚠️" : "")
        );
      });

      const anyMismatch = otherVoters.some(
        (v) => v.gender && v.gender !== currentGdr,
      );
      const mismatchNote = anyMismatch
        ? `<br><small>⚠️ Some picks are for ${currentGdr === "M" ? "girls" : "boys"} — switch gender to compare those</small>`
        : "";

      if (ownPicks === 0) {
        banner.innerHTML =
          `${parts.join(" · ")}${mismatchNote}<br>` +
          `<button class="compare-cta" id="banner-start-btn">Start Swiping to Compare</button>`;
        $("banner-start-btn").addEventListener("click", () => {
          showIntro();
        });
      } else {
        banner.innerHTML = parts.join(" · ") + mismatchNote;
      }
      banner.style.display = "";
    } else {
      $("compare-section").style.display = "none";
      banner.style.display = "none";
    }
  }

  function renderResultList(container, items, cls) {
    container.innerHTML = "";
    const ranks = Object.keys(items)
      .map(Number)
      .sort((a, b) => a - b);

    if (!ranks.length) {
      container.innerHTML = '<div class="result-empty">None yet</div>';
      return;
    }

    for (const rank of ranks) {
      const item = items[rank];
      const row = document.createElement("div");
      row.className = `result-row ${cls}`;

      const nameSpan = document.createElement("span");
      nameSpan.className = "result-name";
      const spells =
        item.spellings || (item.spelling ? [item.spelling] : [item.name]);
      nameSpan.textContent = spells.join(", ");
      if (spells.length === 1 && spells[0] !== item.name) {
        nameSpan.textContent += ` (${item.name})`;
      }

      const rankSpan = document.createElement("span");
      rankSpan.className = "result-rank";
      rankSpan.textContent = `#${rank}`;

      const removeBtn = document.createElement("button");
      removeBtn.className = "result-remove";
      removeBtn.textContent = "×";
      removeBtn.addEventListener("click", () => {
        delete items[rank];
        saveSession();
        showResults();
      });

      row.append(nameSpan, rankSpan, removeBtn);
      container.appendChild(row);
    }
  }

  // ---------------------------------------------------------------
  // Sharing — fully bidirectional
  //
  // Any participant can share and load at any time, mid-session or
  // after finishing. Re-sharing generates a fresh URL with current
  // picks. Loading someone's updated URL replaces their old data.
  // ---------------------------------------------------------------

  function shareDeck() {
    const encoded = encodeSession();
    const url = `${location.origin}${location.pathname}#swipe=${encoded}`;
    copyToClipboard(url, "share-deck-btn");
  }

  function sharePicks() {
    if (!voterName) {
      const name = prompt(
        "Enter your name (so others know whose picks these are):",
      );
      if (!name) return;
      voterName = name.trim();
      saveSession();
      const nameInput = $("voter-name-input");
      if (nameInput) nameInput.value = voterName;
    }
    const encoded = encodePicks();
    const url = `${location.origin}${location.pathname}#picks=${encoded}`;
    const btnId =
      $("swipe-complete").style.display !== "none"
        ? "complete-share-btn"
        : "share-picks-btn";
    copyToClipboard(url, btnId);
  }

  function copyToClipboard(text, btnId) {
    navigator.clipboard.writeText(text).then(
      () => {
        const btn = $(btnId);
        const orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => {
          btn.textContent = orig;
        }, 2000);
      },
      () => prompt("Copy this link:", text),
    );
  }

  // ---------------------------------------------------------------
  // Load other voters' picks
  // ---------------------------------------------------------------

  function showAddVoter() {
    const row = $("add-voter-input-row");
    row.style.display = row.style.display === "none" ? "" : "none";
    $("add-voter-url").value = "";
    $("add-voter-url").focus();
  }

  function loadVoterPicks() {
    const input = $("add-voter-url").value.trim();
    if (!input) return;

    try {
      const hashPart = input.includes("#") ? input.split("#")[1] : input;
      const encoded = hashPart.startsWith("picks=")
        ? hashPart.slice(6)
        : hashPart;
      const data = decodePicks(encoded);
      if (!data || (!data.l && !data.m)) throw new Error("bad data");

      const voterGender = data.g || null;
      const currentGdr = getGender();

      if (voterGender && voterGender !== currentGdr) {
        const label = voterGender === "M" ? "boys" : "girls";
        const currentLabel = currentGdr === "M" ? "boys" : "girls";
        alert(
          `These picks are for ${label}, but you're viewing ${currentLabel}. ` +
            `Switch to ${label} first, then try again.`,
        );
        return;
      }

      const voter = {
        name: data.n || "Partner",
        gender: voterGender || currentGdr,
        liked: {},
        maybe: {},
      };
      for (const r of data.l || []) voter.liked[r] = true;
      for (const r of data.m || []) voter.maybe[r] = true;

      // Replace existing voter with same name (allows updating picks)
      otherVoters = otherVoters.filter((v) => v.name !== voter.name);
      otherVoters.push(voter);

      saveSession();
      $("add-voter-input-row").style.display = "none";
      showResults();

      // Feedback flash
      showToast(
        `Added ${voter.name}'s picks (${Object.keys(voter.liked).length + Object.keys(voter.maybe).length} names)`,
      );
    } catch (e) {
      if (e.message !== "gender_mismatch") {
        alert("Could not read picks. Make sure you paste the full link.");
      }
    }
  }

  function showToast(message) {
    const existing = document.querySelector(".swipe-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.className = "swipe-toast";
    toast.textContent = message;
    $("swipe-overlay").appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  // ---------------------------------------------------------------
  // Comparison — N-way, grouped by consensus level
  // ---------------------------------------------------------------

  function renderComparison() {
    const container = $("compare-results");
    container.innerHTML = "";

    const deckByRank = {};
    for (const d of deck) deckByRank[d.rank] = d;

    const allVoters = [
      { name: voterName || "You", liked, maybe },
      ...otherVoters,
    ];
    const voterCount = allVoters.length;

    // Tally votes per rank
    const rankVotes = {};
    for (const voter of allVoters) {
      for (const r of Object.keys(voter.liked || {})) {
        if (!rankVotes[r]) rankVotes[r] = { likes: 0, maybes: 0, voters: [] };
        rankVotes[r].likes++;
        rankVotes[r].voters.push(voter.name);
      }
      for (const r of Object.keys(voter.maybe || {})) {
        if (!rankVotes[r]) rankVotes[r] = { likes: 0, maybes: 0, voters: [] };
        rankVotes[r].maybes++;
        if (!rankVotes[r].voters.includes(voter.name)) {
          rankVotes[r].voters.push(voter.name);
        }
      }
    }

    const everyone = [];
    const most = [];
    const some = [];

    for (const [r, rv] of Object.entries(rankVotes)) {
      const d = deckByRank[Number(r)];
      if (!d) continue;
      const entry = { rank: Number(r), name: d.name, ...rv };
      if (rv.likes === voterCount) everyone.push(entry);
      else if (rv.likes + rv.maybes >= voterCount) most.push(entry);
      else if (rv.voters.length > 1) some.push(entry);
    }

    const byRank = (a, b) => a.rank - b.rank;
    everyone.sort(byRank);
    most.sort(byRank);
    some.sort(byRank);

    function addSection(title, emoji, items, cls) {
      if (!items.length) return;
      const h = document.createElement("h4");
      h.textContent = `${emoji} ${title} (${items.length.toLocaleString()})`;
      container.appendChild(h);
      for (const item of items) {
        const row = document.createElement("div");
        row.className = `result-row ${cls}`;
        const nameSpan = document.createElement("span");
        nameSpan.className = "result-name";
        nameSpan.textContent = item.name;
        const votersSpan = document.createElement("span");
        votersSpan.className = "result-voters";
        votersSpan.textContent = item.voters.join(", ");
        const rankSpan = document.createElement("span");
        rankSpan.className = "result-rank";
        rankSpan.textContent = `#${item.rank}`;
        row.append(nameSpan, votersSpan, rankSpan);
        container.appendChild(row);
      }
    }

    addSection("Everyone loves", "💛", everyone, "both");
    addSection("Strong contenders", "💙", most, "liked");
    addSection("Worth discussing", "💜", some, "maybe");

    if (!everyone.length && !most.length && !some.length) {
      const ownPicks = Object.keys(liked).length + Object.keys(maybe).length;
      if (ownPicks === 0) {
        container.innerHTML =
          '<div class="result-empty">Start swiping to see how your picks compare</div>';
      } else {
        container.innerHTML =
          '<div class="result-empty">No overlap yet — keep swiping!</div>';
      }
    }

    // Individual voter picks
    const voterDetails = document.createElement("div");
    voterDetails.className = "voter-details";
    for (const voter of otherVoters) {
      const section = document.createElement("details");
      section.className = "voter-detail";
      const summary = document.createElement("summary");
      const likedN = Object.keys(voter.liked || {}).length;
      const maybeN = Object.keys(voter.maybe || {}).length;
      const gLabel =
        voter.gender === "M" ? "boys" : voter.gender === "F" ? "girls" : "";
      summary.textContent = `${voter.name}'s picks — ${likedN} liked, ${maybeN} maybe${gLabel ? ` (${gLabel})` : ""}`;
      section.appendChild(summary);

      const content = document.createElement("div");
      content.className = "voter-detail-content";

      // Their liked names
      if (likedN) {
        const likedList = document.createElement("div");
        likedList.className = "voter-pick-list";
        for (const r of Object.keys(voter.liked)
          .map(Number)
          .sort((a, b) => a - b)) {
          const d = deckByRank[r];
          if (!d) continue;
          const span = document.createElement("span");
          span.className = "voter-pick liked";
          span.textContent = d.name;
          likedList.appendChild(span);
        }
        content.appendChild(likedList);
      }

      // Their maybe names
      if (maybeN) {
        const maybeList = document.createElement("div");
        maybeList.className = "voter-pick-list";
        for (const r of Object.keys(voter.maybe)
          .map(Number)
          .sort((a, b) => a - b)) {
          const d = deckByRank[r];
          if (!d) continue;
          const span = document.createElement("span");
          span.className = "voter-pick maybe";
          span.textContent = d.name;
          maybeList.appendChild(span);
        }
        content.appendChild(maybeList);
      }

      // Remove button
      const removeBtn = document.createElement("button");
      removeBtn.className = "swipe-action-btn secondary small";
      removeBtn.textContent = `Remove ${voter.name}`;
      removeBtn.style.marginTop = "0.5rem";
      removeBtn.addEventListener("click", () => {
        otherVoters = otherVoters.filter((v) => v.name !== voter.name);
        saveSession();
        showToast(`Removed ${voter.name}'s picks`);
        showResults();
      });
      content.appendChild(removeBtn);

      section.appendChild(content);
      voterDetails.appendChild(section);
    }
    container.appendChild(voterDetails);
  }

  // ---------------------------------------------------------------
  // Export / Import
  // ---------------------------------------------------------------

  function exportData() {
    const data = {
      version: deckHash,
      gender: getGender(),
      voter: voterName,
      liked,
      maybe,
      passed: Object.keys(passed).map(Number),
      otherVoters,
      scopeLimit,
      timestamp: new Date().toISOString(),
      deckSize: deck.length,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `babynames-picks-${voterName || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importData(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        if (data.liked) liked = data.liked;
        if (data.maybe) maybe = data.maybe;
        if (data.passed) {
          passed = {};
          for (const r of data.passed) passed[r] = true;
        }
        if (data.voter) voterName = data.voter;
        if (data.otherVoters) otherVoters = data.otherVoters;
        saveSession();
        if (data.version && data.version !== deckHash) {
          alert(
            "Note: This export was created with a different version of the data. Some names may not match.",
          );
        }
        showIntro();
      } catch {
        alert("Could not read file. Make sure it's a valid export.");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  // ---------------------------------------------------------------
  // Gestures (touch + mouse drag on card)
  // ---------------------------------------------------------------

  function setupGestures() {
    let startX = 0;
    let startY = 0;
    let dx = 0;
    let dy = 0;
    let dragging = false;
    const threshold = 80;

    function onStart(e) {
      if ($("swipe-cards").style.display === "none") return;
      dragging = true;
      const pt = e.touches ? e.touches[0] : e;
      startX = pt.clientX;
      startY = pt.clientY;
      dx = 0;
      dy = 0;
      $("swipe-card").style.transition = "none";
    }

    function onMove(e) {
      if (!dragging) return;
      const pt = e.touches ? e.touches[0] : e;
      dx = pt.clientX - startX;
      dy = pt.clientY - startY;
      const card = $("swipe-card");
      card.style.transform = `translate(${dx}px,${dy}px) rotate(${dx * 0.08}deg)`;
      if (dx > 30) card.style.boxShadow = "0 0 40px rgba(76,175,80,0.5)";
      else if (dx < -30) card.style.boxShadow = "0 0 40px rgba(239,83,80,0.5)";
      else if (dy < -30) card.style.boxShadow = "0 0 40px rgba(255,193,7,0.5)";
      else card.style.boxShadow = "";
      e.preventDefault();
    }

    function onEnd() {
      if (!dragging) return;
      dragging = false;
      const card = $("swipe-card");
      card.style.transition = "transform 0.3s ease, opacity 0.25s ease";
      card.style.boxShadow = "";
      if (dx > threshold) act("like");
      else if (dx < -threshold) act("pass");
      else if (dy < -threshold) act("maybe");
      else card.style.transform = "";
    }

    document.addEventListener("mousedown", (e) => {
      if (e.target.closest("#swipe-card")) onStart(e);
    });
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onEnd);
    document.addEventListener(
      "touchstart",
      (e) => {
        if (e.target.closest("#swipe-card")) onStart(e);
      },
      { passive: false },
    );
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("touchend", onEnd);
  }

  // ---------------------------------------------------------------
  // Persistence (localStorage)
  // ---------------------------------------------------------------

  function saveSession() {
    try {
      localStorage.setItem(
        sessionId,
        JSON.stringify({
          liked,
          maybe,
          passed,
          voter: voterName,
          otherVoters,
          scopeLimit,
        }),
      );
    } catch {
      /* storage full or unavailable */
    }
  }

  function loadSession() {
    liked = {};
    maybe = {};
    passed = {};
    voterName = "";
    otherVoters = [];
    actionHistory = [];
    currentIndex = 0;
    scopeLimit = 0;
    try {
      const raw = localStorage.getItem(sessionId);
      if (!raw) return;
      const data = JSON.parse(raw);
      liked = data.liked || {};
      maybe = data.maybe || {};
      passed = data.passed || {};
      voterName = data.voter || "";
      otherVoters = data.otherVoters || [];
      scopeLimit = data.scopeLimit || 0;
    } catch {
      /* corrupt data, start fresh */
    }
  }

  // ---------------------------------------------------------------
  // URL parameter detection (incoming shared links)
  // ---------------------------------------------------------------

  function checkUrlParams() {
    const hash = location.hash.slice(1);
    if (!hash) return;
    const params = new URLSearchParams(hash);

    if (params.get("swipe")) {
      // Shared deck link — currently used for version detection only.
      // Full deck reconstruction would require loading CSV + applying filters,
      // which is better handled by sharing filter state in the main URL hash.
      try {
        JSON.parse(atob(params.get("swipe")));
      } catch {
        /* ignore malformed */
      }
      params.delete("swipe");
      const clean = params.toString();
      window.history.replaceState(
        null,
        "",
        clean ? `#${clean}` : location.pathname,
      );
    }

    if (params.get("picks")) {
      try {
        const picks = decodePicks(params.get("picks"));
        if (picks) {
          const voter = {
            name: picks.n || "Partner",
            gender: picks.g || null,
            liked: {},
            maybe: {},
          };
          for (const r of picks.l || []) voter.liked[r] = true;
          for (const r of picks.m || []) voter.maybe[r] = true;
          // Will merge into session when swipe opens
          otherVoters = otherVoters.filter((v) => v.name !== voter.name);
          otherVoters.push(voter);
          pendingPicks = true;
        }
      } catch {
        /* ignore malformed */
      }
      params.delete("picks");
      const clean = params.toString();
      window.history.replaceState(
        null,
        "",
        clean ? `#${clean}` : location.pathname,
      );
    }
  }

  // ---------------------------------------------------------------
  // Auto-open (called by grid.js after data loads)
  // ---------------------------------------------------------------

  function tryAutoOpen() {
    if (!pendingPicks) return;
    pendingPicks = false;
    // Small delay so table finishes rendering first
    setTimeout(() => {
      openSwipe();
      if (deck.length) showResults();
    }, 100);
  }

  // ---------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      init();
      checkUrlParams();
    });
  } else {
    init();
    checkUrlParams();
  }

  return { open: openSwipe, close: closeSwipe, tryAutoOpen };
})();
