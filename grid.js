// Baby Names - Tabulator-based data grid
// Loads CSV data and renders with filtering, sorting, pagination

const DATA_URLS = {
  M: "data/boys.csv",
  F: "data/girls.csv",
};

const dataCache = {};
let allData = [];
let table = null;
let tableReady = false;
let currentGender = "M";
let dataMaxYear = null;
let activeFilters = {
  letters: [],
  biblical: false,
  unisex: false,
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
    responsiveLayout: "collapse",
    placeholder: "No matching names found",
    pagination: true,
    paginationSize: 100,
    paginationSizeSelector: [50, 100, 250, 500],
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
        minWidth: 120,
        headerFilter: false,
        responsive: 3,
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
        width: 75,
        headerFilter: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
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
        field: "unisex",
        width: 70,
        headerFilter: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
        },
        responsive: 1,
      },
      {
        title: "Letter",
        field: "first_letter",
        width: 65,
        headerFilter: false,
        visible: false,
      },
      {
        title: "Palindrome",
        field: "is_palindrome",
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
        headerFilter: false,
        visible: false,
      },
      {
        title: "Phones",
        field: "pronunciations",
        headerFilter: false,
        visible: false,
      },
      {
        title: "Alliteration",
        field: "alliteration",
        headerFilter: false,
        visible: false,
        formatter: function (cell) {
          return cell.getValue() == 1 ? "Y" : "";
        },
      },
      {
        title: "Allit. First",
        field: "alliteration_first",
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
// Dynamic year detection
// ---------------------------------------------------------------

function detectMaxYear(data) {
  let maxYear = 0;
  for (let i = 0; i < data.length; i++) {
    const ym = Number(data[i].year_max);
    if (ym > maxYear) maxYear = ym;
  }
  return maxYear || new Date().getFullYear();
}

function updateYearReferences(maxYear) {
  document.title =
    "Baby Names \u2013 US Baby Name Search & Explorer (1880\u2013" +
    maxYear +
    ")";
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) {
    metaDesc.setAttribute(
      "content",
      "Browse and filter US baby names from 1880\u2013" +
        maxYear +
        ", phonetically de-duplicated using the CMU Pronouncing Dictionary. Search by gender, popularity rank, syllables, year range, starting letter, name length, peak decade, biblical, unisex, trending, palindrome, and alliteration. Free downloadable CSV datasets.",
    );
  }
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

    if (!table) {
      initTable(allData, function () {
        applyFilters();
      });
    } else if (tableReady) {
      table
        .setData(allData)
        .then(function () {
          applyFilters();
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
      // Ignore stale responses from a previous gender switch
      if (gen !== loadData._gen) return;

      loadingEl.style.display = "none";
      allData = results.data;
      dataCache[gender] = allData;

      if (!dataMaxYear) {
        dataMaxYear = detectMaxYear(allData);
        updateYearReferences(dataMaxYear);
      }

      document.getElementById("total-count").textContent =
        allData.length.toLocaleString();

      if (!table) {
        initTable(allData, function () {
          applyFilters();
        });
      } else if (tableReady) {
        table
          .setData(allData)
          .then(function () {
            applyFilters();
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

  // Year combo filters
  const firstDir = document.getElementById("first-dir").value;
  const firstYearStr = document.getElementById("first-year").value;
  const firstYear = firstYearStr ? Number(firstYearStr) : 0;
  const lastDir = document.getElementById("last-dir").value;
  const lastYearStr = document.getElementById("last-year").value;
  const lastYear = lastYearStr ? Number(lastYearStr) : 0;

  // Toggle filters
  const letterFilters = activeFilters.letters;
  const biblicalFilter = activeFilters.biblical;
  const unisexFilter = activeFilters.unisex;
  const trendingFilter = activeFilters.trending;
  const palindromeFilter = activeFilters.palindrome;
  const alliterationFilter = activeFilters.alliteration;

  const hasAnyFilter =
    searchLower ||
    rankNum ||
    syllNum ||
    lengthVal ||
    decadeNum ||
    firstYear ||
    lastYear ||
    letterFilters.length > 0 ||
    biblicalFilter ||
    unisexFilter ||
    trendingFilter ||
    palindromeFilter ||
    alliterationFilter;

  if (!hasAnyFilter) {
    table.clearFilter(true);
    updateStats();
    return;
  }

  table.setFilter(function (data) {
    // Name search (case-insensitive, also searches spelling variants)
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

    // Name length
    if (lengthVal) {
      const nameLen = String(data.name).length;
      if (lengthVal === "short" && nameLen > 4) return false;
      if (lengthVal === "medium" && (nameLen < 5 || nameLen > 6)) return false;
      if (lengthVal === "long" && nameLen < 7) return false;
    }

    // Peak decade
    if (decadeNum) {
      if (decadeNum === 1940) {
        // "1940s & earlier"
        if (data.year_peak >= 1950) return false;
      } else {
        if (data.year_peak < decadeNum || data.year_peak >= decadeNum + 10)
          return false;
      }
    }

    // First Used (year_min)
    if (firstYear) {
      if (firstDir === "after" && data.year_min < firstYear) return false;
      if (firstDir === "before" && data.year_min > firstYear) return false;
    }

    // Last Used (year_max)
    if (lastYear) {
      if (lastDir === "after" && data.year_max < lastYear) return false;
      if (lastDir === "before" && data.year_max > lastYear) return false;
    }

    // Starting letters (multi-select)
    if (
      letterFilters.length > 0 &&
      letterFilters.indexOf(data.first_letter) === -1
    ) {
      return false;
    }

    // Boolean toggles
    if (biblicalFilter && data.biblical != 1) return false;
    if (unisexFilter && data.unisex != 1) return false;
    if (trendingFilter && data.year_peak < 2010) return false;
    if (palindromeFilter && data.is_palindrome != 1) return false;
    if (alliterationFilter && data.alliteration != 1) return false;

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
    loadData(btn.dataset.gender);
  });
});

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
  "first-dir",
  "last-dir",
].forEach(function (id) {
  document.getElementById(id).addEventListener("change", applyFilters);
});

// Year inputs
const YEAR_MIN = 1880;
const YEAR_MAX = new Date().getFullYear();

function clampYear(value, lo, hi) {
  const n = parseInt(value, 10);
  if (isNaN(n)) return "";
  if (n < lo) return String(lo);
  if (n > hi) return String(hi);
  return String(n);
}

["first-year", "last-year"].forEach(function (id) {
  const el = document.getElementById(id);
  el.addEventListener("input", function () {
    this.value = this.value.replace(/[^0-9]/g, "");
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(applyFilters, 300);
  });
  el.addEventListener("blur", function () {
    if (this.value) {
      this.value = clampYear(this.value, YEAR_MIN, YEAR_MAX);
    }
    applyFilters();
  });
});

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

// Toggle buttons (Biblical, Unisex, Trending, Palindrome, Alliteration)
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
  document.getElementById("first-dir").value = "after";
  document.getElementById("first-year").value = "";
  document.getElementById("last-dir").value = "after";
  document.getElementById("last-year").value = "";
  activeFilters.letters = [];
  activeFilters.biblical = false;
  activeFilters.unisex = false;
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

  // Year combos
  const firstYear = document.getElementById("first-year").value;
  if (firstYear) {
    const firstDir = document.getElementById("first-dir").value;
    params.set("fy", firstYear);
    if (firstDir !== "after") params.set("fd", firstDir);
  }
  const lastYear = document.getElementById("last-year").value;
  if (lastYear) {
    const lastDir = document.getElementById("last-dir").value;
    params.set("ly", lastYear);
    if (lastDir !== "after") params.set("ld", lastDir);
  }

  if (activeFilters.letters.length > 0)
    params.set("letters", [...activeFilters.letters].sort().join(","));
  if (activeFilters.biblical) params.set("biblical", "1");
  if (activeFilters.unisex) params.set("unisex", "1");
  if (activeFilters.trending) params.set("trending", "1");
  if (activeFilters.palindrome) params.set("palindrome", "1");
  if (activeFilters.alliteration) params.set("alliteration", "1");

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

  // Year combos
  if (params.get("fy")) {
    document.getElementById("first-year").value = params.get("fy");
    if (params.get("fd"))
      document.getElementById("first-dir").value = params.get("fd");
  }
  if (params.get("ly")) {
    document.getElementById("last-year").value = params.get("ly");
    if (params.get("ld"))
      document.getElementById("last-dir").value = params.get("ld");
  }

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
  // Backward compat: single letter param
  if (
    !lettersParam &&
    params.get("letter") &&
    isValidLetter(params.get("letter"))
  ) {
    const singleLetter = params.get("letter");
    activeFilters.letters = [singleLetter];
    const chip = document.querySelector(
      '.letter-chip[data-letter="' + singleLetter + '"]',
    );
    if (chip) {
      chip.classList.add("active");
      chip.setAttribute("aria-pressed", "true");
    }
  }

  // Boolean toggles
  ["biblical", "unisex", "trending", "palindrome", "alliteration"].forEach(
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
