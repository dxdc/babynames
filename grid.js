// Baby Names - Tabulator-based data grid
// Loads CSV data and renders with filtering, sorting, virtual scrolling

const DATA_VERSION = "2.2.0"; // bump when CSV schema or data changes

const DATA_URLS = {
  M: `data/boys.csv?v=${DATA_VERSION}`,
  F: `data/girls.csv?v=${DATA_VERSION}`,
};

const GENDER_LABELS = { M: "Boys", F: "Girls" };
const TRENDING_WINDOW = 15; // "trending" = peaked within last N years of data

const dataCache = {};
let allData = [];
let table = null;
let tableReady = false;
let currentGender = "M";
let dataMaxYear = null;
let dataMinYear = null;
let activeFilters = {
  letters: [],
  biblical: false,
  trending: false,
  palindrome: false,
  alliteration: false,
};

// ---------------------------------------------------------------
// Table setup — waits for tableBuilt before applying filters
// ---------------------------------------------------------------

function initTable(data, onReady) {
  table = new Tabulator("#table-container", {
    height: "70vh",
    data: data,
    layout: "fitColumns",
    responsiveLayout: "hide",
    placeholder: "No matching names found",
    columns: [
      {
        title: "Rank",
        field: "rank",
        sorter: "number",
        width: 70,
        headerFilter: false,
      },
      {
        title: "Name",
        field: "name",
        sorter: "string",
        minWidth: 100,
        headerFilter: false,
      },
      {
        title: "Variations",
        field: "spelling_variants",
        sorter: "string",
        minWidth: 140,
        headerFilter: false,
        responsive: 3,
        formatter: function (cell) {
          const val = cell.getValue();
          if (!val) return "";
          return val.split(" ").join(", ");
        },
        tooltip: function (e, cell) {
          const val = cell.getValue();
          if (!val) return "";
          return val.split(" ").join(", ");
        },
      },
      {
        title: "Count",
        field: "total_count",
        sorter: "number",
        width: 90,
        formatter: function (cell) {
          return Number(cell.getValue()).toLocaleString();
        },
        headerFilter: false,
      },
      {
        title: "Cum%",
        field: "cumulative_pct",
        sorter: "number",
        width: 70,
        tooltip:
          "Cumulative percentage of all babies with this name or higher-ranked names",
        formatter: function (cell) {
          return Number(cell.getValue()).toFixed(1);
        },
        headerFilter: false,
        responsive: 1,
      },
      {
        title: "Yr Min",
        field: "year_min",
        sorter: "number",
        width: 80,
        headerFilter: false,
        responsive: 2,
      },
      {
        title: "Yr Max",
        field: "year_max",
        sorter: "number",
        width: 80,
        headerFilter: false,
        responsive: 2,
      },
      {
        title: "Yr Pop",
        field: "year_peak",
        sorter: "number",
        width: 80,
        headerFilter: false,
        responsive: 2,
      },
      {
        title: "Biblical",
        field: "biblical",
        sorter: "string",
        width: 80,
        headerFilter: false,
        formatter: function (cell) {
          var val = cell.getValue();
          return val || "";
        },
        responsive: 1,
      },
      {
        title: "Syllables",
        field: "syllables",
        sorter: "number",
        width: 85,
        headerFilter: false,
        responsive: 1,
      },
      {
        title: "Unisex",
        field: "unisex_pct",
        sorter: "number",
        width: 90,
        headerFilter: false,
        tooltip:
          "Minority gender share (50% = perfectly balanced). Shows dominant gender.",
        formatter: function (cell) {
          const val = cell.getValue();
          if (val == null || val === "") return "";
          const dom = cell.getRow().getData().unisex_dominant;
          const label = dom === "M" ? "♂" : dom === "F" ? "♀" : "";
          return val + "% " + label;
        },
        responsive: 1,
      },
      {
        title: "Nickname Of",
        field: "nickname_of",
        sorter: "string",
        width: 120,
        headerFilter: false,
        formatter: function (cell) {
          var val = cell.getValue();
          if (!val) return "";
          return val.split(" ").join(", ");
        },
        tooltip: function (e, cell) {
          var val = cell.getValue();
          if (!val) return "";
          return val.split(" ").join(", ");
        },
        responsive: 2,
      },
      {
        title: "Letter",
        field: "first_letter",
        sorter: "string",
        width: 65,
        headerFilter: false,
        visible: false,
      },
      {
        title: "Palindrome",
        field: "is_palindrome",
        sorter: "number",
        width: 90,
        headerFilter: false,
        visible: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
        },
      },
      {
        title: "Stresses",
        field: "stresses",
        sorter: "string",
        headerFilter: false,
        visible: false,
      },
      {
        title: "Phones",
        field: "pronunciations",
        sorter: "string",
        headerFilter: false,
        visible: false,
      },
      {
        title: "Alliteration",
        field: "alliteration",
        sorter: "number",
        headerFilter: false,
        visible: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
        },
      },
      {
        title: "Allit. First",
        field: "alliteration_first",
        sorter: "number",
        headerFilter: false,
        visible: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
        },
      },
    ],
    initialSort: [{ column: "rank", dir: "asc" }],
    dataFiltered: function () {
      updateStats();
    },
    dataLoaded: function () {
      updateStats();
    },
  });

  table.on("tableBuilt", function () {
    tableReady = true;
    if (onReady) onReady();
  });
}

// ---------------------------------------------------------------
// Dynamic year detection and data info
// ---------------------------------------------------------------

function detectYearRange(data) {
  let minY = 9999;
  let maxY = 0;
  for (let i = 0; i < data.length; i++) {
    const ymin = Number(data[i].year_min);
    const ymax = Number(data[i].year_max);
    if (ymin < minY) minY = ymin;
    if (ymax > maxY) maxY = ymax;
  }
  return { min: minY || 1880, max: maxY || new Date().getFullYear() };
}

function updatePageMeta() {
  if (!dataMinYear || !dataMaxYear) return;
  document.title =
    "Baby Names \u2013 Search & Filter 100k+ US Baby Names (" +
    dataMinYear +
    "\u2013" +
    dataMaxYear +
    ")";
}

function updateDataInfo() {
  const label = GENDER_LABELS[currentGender] || currentGender;
  const count = allData.length.toLocaleString();
  const range =
    dataMinYear && dataMaxYear ? dataMinYear + "\u2013" + dataMaxYear : "";
  document.getElementById("data-info").textContent =
    label + " \u00b7 " + count + " names" + (range ? " \u00b7 " + range : "");
}

// ---------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------

function loadData(gender) {
  currentGender = gender;
  loadData._gen = (loadData._gen || 0) + 1;
  const gen = loadData._gen;

  if (dataCache[gender]) {
    allData = dataCache[gender];
    document.getElementById("total-count").textContent =
      allData.length.toLocaleString();
    updateDataInfo();

    if (!table) {
      initTable(allData, function () {
        applyFilters();
        if (typeof swipe !== "undefined" && swipe.tryAutoOpen) {
          swipe.tryAutoOpen();
        }
      });
    } else if (tableReady) {
      table
        .setData(allData)
        .then(function () {
          applyFilters();
          if (typeof swipe !== "undefined" && swipe.tryAutoOpen) {
            swipe.tryAutoOpen();
          }
        })
        .catch(function (err) {
          console.error("setData error:", err);
        });
    }
    return;
  }

  const url = DATA_URLS[gender];
  const loadingEl = document.getElementById("loading");
  loadingEl.textContent = "Loading baby names\u2026";
  loadingEl.style.display = "block";

  Papa.parse(url, {
    download: true,
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: function (results) {
      if (gen !== loadData._gen) return;

      loadingEl.style.display = "none";
      allData = results.data;
      dataCache[gender] = allData;

      if (!dataMaxYear) {
        const range = detectYearRange(allData);
        dataMinYear = range.min;
        dataMaxYear = range.max;
        updatePageMeta();
      }

      document.getElementById("total-count").textContent =
        allData.length.toLocaleString();
      updateDataInfo();

      if (!table) {
        initTable(allData, function () {
          applyFilters();
          if (typeof swipe !== "undefined" && swipe.tryAutoOpen) {
            swipe.tryAutoOpen();
          }
        });
      } else if (tableReady) {
        table
          .setData(allData)
          .then(function () {
            applyFilters();
            if (typeof swipe !== "undefined" && swipe.tryAutoOpen) {
              swipe.tryAutoOpen();
            }
          })
          .catch(function (err) {
            console.error("setData error:", err);
          });
      }
    },
    error: function () {
      if (gen !== loadData._gen) return;
      loadingEl.textContent =
        "Failed to load data. Please try refreshing the page.";
    },
  });
}

// ---------------------------------------------------------------
// Filtering — single custom function for Tabulator 6.x compat
// ---------------------------------------------------------------

function applyFilters() {
  if (!table || !tableReady) return;

  // Text / dropdown filters
  const search = document.getElementById("name-search").value.trim();
  const searchLower = search ? search.toLowerCase() : "";
  const rankVal = document.getElementById("rank-filter").value;
  const rankNum = rankVal ? Number(rankVal) : 0;
  const syllVal = document.getElementById("syllable-filter").value;
  const syllNum = syllVal ? Number(syllVal) : 0;
  const lengthVal = document.getElementById("length-filter").value;
  const decadeVal = document.getElementById("decade-filter").value;
  const decadeNum = decadeVal ? Number(decadeVal) : 0;

  // Year filter
  const yearMode = document.getElementById("year-mode").value;
  const yearValStr = document.getElementById("year-value").value;
  const yearVal = yearValStr ? Number(yearValStr) : 0;

  // Unisex dropdown
  const unisexVal = document.getElementById("unisex-filter").value;
  const unisexMin = unisexVal ? Number(unisexVal) : 0;

  // Toggle filters
  const letterFilters = activeFilters.letters;
  const biblicalFilter = activeFilters.biblical;
  const trendingFilter = activeFilters.trending;
  const palindromeFilter = activeFilters.palindrome;
  const alliterationFilter = activeFilters.alliteration;

  // Variants dropdown
  const variantsVal = document.getElementById("variants-filter").value;

  // Trending threshold: peaked within last TRENDING_WINDOW years of data
  const trendingCutoff = dataMaxYear ? dataMaxYear - TRENDING_WINDOW + 1 : 2010;

  const hasAnyFilter =
    searchLower ||
    rankNum ||
    syllNum ||
    lengthVal ||
    decadeNum ||
    (yearMode && yearVal) ||
    unisexMin ||
    variantsVal ||
    letterFilters.length > 0 ||
    biblicalFilter ||
    trendingFilter ||
    palindromeFilter ||
    alliterationFilter;

  if (!hasAnyFilter) {
    table.clearFilter(true);
    updateStats();
    return;
  }

  table.setFilter(function (data) {
    // Name search
    if (searchLower) {
      const nameMatch = String(data.name).toLowerCase().includes(searchLower);
      if (!nameMatch) {
        const variants = data.spelling_variants;
        if (
          !variants ||
          !String(variants).toLowerCase().includes(searchLower)
        ) {
          return false;
        }
      }
    }

    // Rank
    if (rankNum && data.rank > rankNum) return false;

    // Syllables
    if (syllVal === "4") {
      if (data.syllables < 4) return false;
    } else if (syllNum) {
      if (data.syllables !== syllNum) return false;
    }

    // Name length (any spelling — primary or any variant)
    if (lengthVal) {
      const allNames = [String(data.name)];
      if (data.spelling_variants) {
        String(data.spelling_variants)
          .split(" ")
          .forEach(function (v) {
            if (v) allNames.push(v);
          });
      }
      const minLen = Math.min.apply(
        null,
        allNames.map(function (n) {
          return n.length;
        }),
      );
      const maxLen = Math.max.apply(
        null,
        allNames.map(function (n) {
          return n.length;
        }),
      );
      if (lengthVal === "short" && minLen > 4) return false;
      if (lengthVal === "medium" && (minLen > 6 || maxLen < 5)) return false;
      if (lengthVal === "long" && maxLen < 7) return false;
    }

    // Peak decade
    if (decadeNum) {
      if (decadeNum === 1940) {
        if (data.year_peak >= 1950) return false;
      } else {
        if (data.year_peak < decadeNum || data.year_peak >= decadeNum + 10)
          return false;
      }
    }

    // Year filter
    if (yearMode && yearVal) {
      if (yearMode === "appeared-after" && data.year_min < yearVal)
        return false;
      if (yearMode === "appeared-before" && data.year_min > yearVal)
        return false;
      if (yearMode === "retired-before" && data.year_max > yearVal)
        return false;
      if (yearMode === "still-used-after" && data.year_max < yearVal)
        return false;
    }

    // Unisex share
    if (
      unisexMin &&
      (data.unisex_pct == null ||
        data.unisex_pct === "" ||
        data.unisex_pct < unisexMin)
    )
      return false;

    // Starting letters (multi-select)
    if (
      letterFilters.length > 0 &&
      letterFilters.indexOf(data.first_letter) === -1
    ) {
      return false;
    }

    // Boolean toggles
    if (biblicalFilter && !data.biblical) return false;
    if (trendingFilter && data.year_peak < trendingCutoff) return false;
    if (palindromeFilter && data.is_palindrome != 1) return false;
    if (alliterationFilter && data.alliteration != 1) return false;
    if (variantsVal === "has" && !data.spelling_variants) return false;
    if (variantsVal === "no" && data.spelling_variants) return false;

    return true;
  });
  updateStats();
}

function updateStats() {
  if (!table) return;
  const shown = table.getDataCount("active");
  document.getElementById("shown-count").textContent = shown.toLocaleString();
}

// ---------------------------------------------------------------
// UI event handlers
// ---------------------------------------------------------------

// Gender buttons
document.querySelectorAll(".gender-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    document.querySelectorAll(".gender-btn").forEach(function (b) {
      b.classList.remove("active");
    });
    btn.classList.add("active");
    document.documentElement.setAttribute("data-gender", btn.dataset.gender);
    loadData(btn.dataset.gender);
  });
});

// Set initial gender attribute
document.documentElement.setAttribute("data-gender", "M");

// Name search with debouncing
let searchTimeout;
document.getElementById("name-search").addEventListener("input", function () {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(applyFilters, 200);
});

// Dropdowns (instant apply)
[
  "rank-filter",
  "syllable-filter",
  "length-filter",
  "decade-filter",
  "year-mode",
  "unisex-filter",
  "variants-filter",
].forEach(function (id) {
  document.getElementById(id).addEventListener("change", applyFilters);
});

// Year input
const YEAR_MIN = 1880;
const YEAR_MAX = new Date().getFullYear();

function clampYear(value, lo, hi) {
  const n = parseInt(value, 10);
  if (isNaN(n)) return "";
  if (n < lo) return String(lo);
  if (n > hi) return String(hi);
  return String(n);
}

(function () {
  const modeEl = document.getElementById("year-mode");
  const valEl = document.getElementById("year-value");

  // Enable/disable year input based on mode selection
  modeEl.addEventListener("change", function () {
    valEl.disabled = !this.value;
    if (!this.value) {
      valEl.value = "";
    } else {
      valEl.focus();
    }
  });

  valEl.addEventListener("input", function () {
    this.value = this.value.replace(/[^0-9]/g, "");
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(applyFilters, 300);
  });
  valEl.addEventListener("blur", function () {
    if (this.value) {
      this.value = clampYear(this.value, YEAR_MIN, YEAR_MAX);
    }
    applyFilters();
  });
})();

// Letter chips — multi-select
(function () {
  const container = document.getElementById("letter-chips");
  for (let i = 65; i <= 90; i++) {
    const letter = String.fromCharCode(i);
    const chip = document.createElement("span");
    chip.className = "letter-chip";
    chip.textContent = letter;
    chip.dataset.letter = letter;
    chip.tabIndex = 0;
    chip.setAttribute("role", "button");
    chip.setAttribute("aria-label", "Filter by letter " + letter);
    chip.setAttribute("aria-pressed", "false");
    chip.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        this.click();
      }
    });
    chip.addEventListener("click", function () {
      const clickedLetter = this.dataset.letter;
      const idx = activeFilters.letters.indexOf(clickedLetter);
      if (idx !== -1) {
        activeFilters.letters.splice(idx, 1);
        this.classList.remove("active");
        this.setAttribute("aria-pressed", "false");
      } else {
        activeFilters.letters.push(clickedLetter);
        this.classList.add("active");
        this.setAttribute("aria-pressed", "true");
      }
      applyFilters();
    });
    container.appendChild(chip);
  }

  // Mobile expand/collapse toggle
  const toggle = document.createElement("button");
  toggle.className = "letter-chips-toggle";
  toggle.textContent = "More";
  toggle.setAttribute("aria-label", "Show all letters");
  toggle.addEventListener("click", function () {
    const expanded = container.classList.toggle("expanded");
    toggle.textContent = expanded ? "Less" : "More";
    toggle.setAttribute(
      "aria-label",
      expanded ? "Show fewer letters" : "Show all letters",
    );
  });
  container.parentNode.appendChild(toggle);
})();

// Toggle buttons (Biblical, Trending, Palindrome, Alliteration)
document.querySelectorAll(".filter-toggle").forEach(function (btn) {
  btn.addEventListener("click", function () {
    const filter = btn.dataset.filter;
    activeFilters[filter] = !activeFilters[filter];
    btn.classList.toggle("active");
    btn.setAttribute("aria-pressed", String(activeFilters[filter]));
    applyFilters();
  });
});

// Clear all filters
document.getElementById("clear-filters").addEventListener("click", function () {
  document.getElementById("name-search").value = "";
  document.getElementById("rank-filter").value = "";
  document.getElementById("syllable-filter").value = "";
  document.getElementById("length-filter").value = "";
  document.getElementById("decade-filter").value = "";
  document.getElementById("year-mode").value = "";
  document.getElementById("year-value").value = "";
  document.getElementById("year-value").disabled = true;
  document.getElementById("unisex-filter").value = "";
  document.getElementById("variants-filter").value = "";
  activeFilters.letters = [];
  activeFilters.biblical = false;
  activeFilters.trending = false;
  activeFilters.palindrome = false;
  activeFilters.alliteration = false;
  document
    .querySelectorAll(".letter-chip, .filter-toggle")
    .forEach(function (el) {
      el.classList.remove("active");
      el.setAttribute("aria-pressed", "false");
    });
  applyFilters();
});

// Title link — clear all filters and scroll to top
document.getElementById("title-link").addEventListener("click", function (e) {
  e.preventDefault();
  document.getElementById("clear-filters").click();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// Dark mode toggle
document.getElementById("theme-toggle").addEventListener("click", function () {
  const html = document.documentElement;
  const current = html.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
  this.textContent = next === "dark" ? "Light" : "Dark";
  localStorage.setItem("theme", next);
});

// Restore theme from localStorage
(function () {
  const saved = localStorage.getItem("theme");
  if (saved) {
    document.documentElement.setAttribute("data-theme", saved);
    document.getElementById("theme-toggle").textContent =
      saved === "dark" ? "Light" : "Dark";
  }
})();

// ---------------------------------------------------------------
// URL hash state for shareable filters
// ---------------------------------------------------------------

function saveStateToHash() {
  const params = new URLSearchParams();
  if (currentGender !== "M") params.set("g", currentGender);
  const search = document.getElementById("name-search").value.trim();
  if (search) params.set("q", search);
  const rank = document.getElementById("rank-filter").value;
  if (rank) params.set("rank", rank);
  const syll = document.getElementById("syllable-filter").value;
  if (syll) params.set("syll", syll);
  const length = document.getElementById("length-filter").value;
  if (length) params.set("len", length);
  const decade = document.getElementById("decade-filter").value;
  if (decade) params.set("decade", decade);

  // Year filter
  const yearMode = document.getElementById("year-mode").value;
  const yearVal = document.getElementById("year-value").value;
  if (yearMode && yearVal) {
    params.set("ym", yearMode);
    params.set("yv", yearVal);
  }

  // Unisex
  const unisex = document.getElementById("unisex-filter").value;
  if (unisex) params.set("unisex", unisex);

  if (activeFilters.letters.length > 0)
    params.set("letters", [...activeFilters.letters].sort().join(","));
  if (activeFilters.biblical) params.set("biblical", "1");
  if (activeFilters.trending) params.set("trending", "1");
  if (activeFilters.palindrome) params.set("palindrome", "1");
  if (activeFilters.alliteration) params.set("alliteration", "1");
  const variants = document.getElementById("variants-filter").value;
  if (variants) params.set("variants", variants);

  const hash = params.toString();
  history.replaceState(null, "", hash ? "#" + hash : location.pathname);
}

function isValidLetter(value) {
  return typeof value === "string" && /^[A-Z]$/.test(value);
}

function loadStateFromHash() {
  const hash = location.hash.slice(1);
  if (!hash) return;
  const params = new URLSearchParams(hash);

  if (params.get("g") === "F") {
    document.querySelectorAll(".gender-btn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.gender === "F");
    });
    currentGender = "F";
    document.documentElement.setAttribute("data-gender", "F");
  }
  if (params.get("q"))
    document.getElementById("name-search").value = params.get("q");
  if (params.get("rank"))
    document.getElementById("rank-filter").value = params.get("rank");
  if (params.get("syll"))
    document.getElementById("syllable-filter").value = params.get("syll");
  if (params.get("len"))
    document.getElementById("length-filter").value = params.get("len");
  if (params.get("decade"))
    document.getElementById("decade-filter").value = params.get("decade");

  // Year filter
  if (params.get("ym") && params.get("yv")) {
    document.getElementById("year-mode").value = params.get("ym");
    document.getElementById("year-value").value = params.get("yv");
    document.getElementById("year-value").disabled = false;
  }

  // Unisex
  if (params.get("unisex"))
    document.getElementById("unisex-filter").value = params.get("unisex");

  // Multi-select letters
  const lettersParam = params.get("letters");
  if (lettersParam) {
    const letters = lettersParam.split(",").filter(isValidLetter);
    activeFilters.letters = letters;
    letters.forEach(function (l) {
      const chip = document.querySelector(
        '.letter-chip[data-letter="' + l + '"]',
      );
      if (chip) {
        chip.classList.add("active");
        chip.setAttribute("aria-pressed", "true");
      }
    });
  }
  // Variants dropdown
  if (params.get("variants"))
    document.getElementById("variants-filter").value = params.get("variants");

  // Boolean toggles
  ["biblical", "trending", "palindrome", "alliteration"].forEach(
    function (key) {
      if (params.get(key)) {
        activeFilters[key] = true;
        const btn = document.querySelector(
          '.filter-toggle[data-filter="' + key + '"]',
        );
        if (btn) {
          btn.classList.add("active");
          btn.setAttribute("aria-pressed", "true");
        }
      }
    },
  );
}

// Save state whenever filters change
const origApplyFilters = applyFilters;
applyFilters = function () {
  origApplyFilters();
  saveStateToHash();
};

// Load state on startup, then load data
loadStateFromHash();
loadData(currentGender);

// ---------------------------------------------------------------
// Public API for swipe mode
// ---------------------------------------------------------------

function getSwipeDeck() {
  if (!table || !tableReady) return [];
  return table.getData("active");
}

function getCurrentGender() {
  return currentGender;
}
