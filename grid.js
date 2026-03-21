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
  palindrome: false,
  alliteration: false,
};

// ---------------------------------------------------------------
// Table setup — waits for tableBuilt before applying filters
// ---------------------------------------------------------------

function initTable(data, onReady) {
  document.getElementById("loading").style.display = "none";

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

  // Wait for Tabulator to finish building before calling any methods
  table.on("tableBuilt", function () {
    tableReady = true;
    if (onReady) onReady();
  });
}

// ---------------------------------------------------------------
// Dynamic year detection
// ---------------------------------------------------------------

function detectMaxYear(data) {
  var maxYear = 0;
  for (var i = 0; i < data.length; i++) {
    var ym = Number(data[i].year_max);
    if (ym > maxYear) maxYear = ym;
  }
  return maxYear || new Date().getFullYear();
}

function updateYearReferences(maxYear) {
  document.getElementById("year-max").placeholder = String(maxYear);
  document.title =
    "Baby Names \u2013 US Baby Name Search & Explorer (1880\u2013" +
    maxYear +
    ")";
  var metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) {
    metaDesc.setAttribute(
      "content",
      "Browse and filter US baby names from 1880\u2013" +
        maxYear +
        ", phonetically de-duplicated using the CMU Pronouncing Dictionary. Search by gender, popularity rank, syllables, year range, starting letter, biblical, unisex, palindrome, and alliteration names. Free downloadable CSV datasets.",
    );
  }
}

// ---------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------

function loadData(gender) {
  currentGender = gender;

  if (dataCache[gender]) {
    allData = dataCache[gender];
    document.getElementById("total-count").textContent =
      allData.length.toLocaleString();

    if (!table) {
      initTable(allData, function () {
        applyFilters();
      });
    } else if (tableReady) {
      table.setData(allData).then(function () {
        applyFilters();
      });
    }
    return;
  }

  const url = DATA_URLS[gender];
  document.getElementById("loading").style.display = "block";

  Papa.parse(url, {
    download: true,
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: function (results) {
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
        table.setData(allData).then(function () {
          applyFilters();
        });
      }
    },
    error: function () {
      document.getElementById("loading").textContent =
        "Failed to load data. Please try refreshing the page.";
    },
  });
}

// ---------------------------------------------------------------
// Filtering — single custom function for Tabulator 6.x compat
// ---------------------------------------------------------------

function applyFilters() {
  if (!table || !tableReady) return;

  const search = document.getElementById("name-search").value.trim();
  const searchLower = search ? search.toLowerCase() : "";
  const rankVal = document.getElementById("rank-filter").value;
  const rankNum = rankVal ? Number(rankVal) : 0;
  const syllVal = document.getElementById("syllable-filter").value;
  const syllNum = syllVal ? Number(syllVal) : 0;
  const yearMin = document.getElementById("year-min").value;
  const yearMinNum = yearMin ? Number(yearMin) : 0;
  const yearMax = document.getElementById("year-max").value;
  const yearMaxNum = yearMax ? Number(yearMax) : 0;
  const letterFilters = activeFilters.letters;
  const biblicalFilter = activeFilters.biblical;
  const unisexFilter = activeFilters.unisex;
  const palindromeFilter = activeFilters.palindrome;
  const alliterationFilter = activeFilters.alliteration;

  const hasAnyFilter =
    searchLower ||
    rankNum ||
    syllNum ||
    yearMinNum ||
    yearMaxNum ||
    letterFilters.length > 0 ||
    biblicalFilter ||
    unisexFilter ||
    palindromeFilter ||
    alliterationFilter;

  if (!hasAnyFilter) {
    table.clearFilter(true);
    return;
  }

  table.setFilter(function (data) {
    // Name search (case-insensitive, also searches spelling variants)
    if (searchLower) {
      var nameMatch = String(data.name).toLowerCase().includes(searchLower);
      if (!nameMatch) {
        var variants = data.spelling_variants;
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

    // Active After: name was still in use after this year
    if (yearMinNum && data.year_max < yearMinNum) return false;

    // Active Before: name existed before this year
    if (yearMaxNum && data.year_min > yearMaxNum) return false;

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
    if (palindromeFilter && data.is_palindrome != 1) return false;
    if (alliterationFilter && data.alliteration != 1) return false;

    return true;
  });
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

// Dropdowns
["rank-filter", "syllable-filter"].forEach(function (id) {
  document.getElementById(id).addEventListener("change", applyFilters);
});

// Year inputs
var YEAR_MIN = 1880;
var YEAR_MAX = new Date().getFullYear();

function clampYear(value, lo, hi) {
  var n = parseInt(value, 10);
  if (isNaN(n)) return "";
  if (n < lo) return String(lo);
  if (n > hi) return String(hi);
  return String(n);
}

function validateYearRange() {
  var afterEl = document.getElementById("year-min");
  var beforeEl = document.getElementById("year-max");
  var afterVal = afterEl.value ? parseInt(afterEl.value, 10) : null;
  var beforeVal = beforeEl.value ? parseInt(beforeEl.value, 10) : null;
  if (afterVal !== null && beforeVal !== null && afterVal > beforeVal) {
    beforeEl.value = String(afterVal);
  }
}

["year-min", "year-max"].forEach(function (id) {
  var el = document.getElementById(id);
  el.addEventListener("input", function () {
    this.value = this.value.replace(/[^0-9]/g, "");
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(applyFilters, 300);
  });
  el.addEventListener("blur", function () {
    if (this.value) {
      this.value = clampYear(this.value, YEAR_MIN, YEAR_MAX);
    }
    validateYearRange();
    applyFilters();
  });
});

// Letter chips — multi-select
(function () {
  var container = document.getElementById("letter-chips");
  for (var i = 65; i <= 90; i++) {
    var letter = String.fromCharCode(i);
    var chip = document.createElement("span");
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
      var clickedLetter = this.dataset.letter;
      var idx = activeFilters.letters.indexOf(clickedLetter);
      if (idx !== -1) {
        // Deselect
        activeFilters.letters.splice(idx, 1);
        this.classList.remove("active");
        this.setAttribute("aria-pressed", "false");
      } else {
        // Select (add to multi-select)
        activeFilters.letters.push(clickedLetter);
        this.classList.add("active");
        this.setAttribute("aria-pressed", "true");
      }
      applyFilters();
    });
    container.appendChild(chip);
  }

  // Mobile expand/collapse toggle
  var toggle = document.createElement("button");
  toggle.className = "letter-chips-toggle";
  toggle.textContent = "More";
  toggle.setAttribute("aria-label", "Show all letters");
  toggle.addEventListener("click", function () {
    var expanded = container.classList.toggle("expanded");
    toggle.textContent = expanded ? "Less" : "More";
    toggle.setAttribute(
      "aria-label",
      expanded ? "Show fewer letters" : "Show all letters",
    );
  });
  container.parentNode.appendChild(toggle);
})();

// Toggle buttons (Biblical, Unisex, Palindrome, Alliteration)
document.querySelectorAll(".filter-toggle").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var filter = btn.dataset.filter;
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
  document.getElementById("year-min").value = "";
  document.getElementById("year-max").value = "";
  activeFilters.letters = [];
  activeFilters.biblical = false;
  activeFilters.unisex = false;
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
  var html = document.documentElement;
  var current = html.getAttribute("data-theme");
  var next = current === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
  this.textContent = next === "dark" ? "Light" : "Dark";
  localStorage.setItem("theme", next);
});

// Restore theme from localStorage
(function () {
  var saved = localStorage.getItem("theme");
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
  var params = new URLSearchParams();
  if (currentGender !== "M") params.set("g", currentGender);
  var search = document.getElementById("name-search").value.trim();
  if (search) params.set("q", search);
  var rank = document.getElementById("rank-filter").value;
  if (rank) params.set("rank", rank);
  var syll = document.getElementById("syllable-filter").value;
  if (syll) params.set("syll", syll);
  var ymin = document.getElementById("year-min").value;
  if (ymin) params.set("ymin", ymin);
  var ymax = document.getElementById("year-max").value;
  if (ymax) params.set("ymax", ymax);
  if (activeFilters.letters.length > 0)
    params.set("letters", activeFilters.letters.sort().join(","));
  if (activeFilters.biblical) params.set("biblical", "1");
  if (activeFilters.unisex) params.set("unisex", "1");
  if (activeFilters.palindrome) params.set("palindrome", "1");
  if (activeFilters.alliteration) params.set("alliteration", "1");

  var hash = params.toString();
  history.replaceState(null, "", hash ? "#" + hash : location.pathname);
}

function isValidLetter(value) {
  return typeof value === "string" && /^[A-Z]$/.test(value);
}

function loadStateFromHash() {
  var hash = location.hash.slice(1);
  if (!hash) return;
  var params = new URLSearchParams(hash);

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
  if (params.get("ymin"))
    document.getElementById("year-min").value = params.get("ymin");
  if (params.get("ymax"))
    document.getElementById("year-max").value = params.get("ymax");

  // Multi-select letters (new format: letters=A,B,C)
  var lettersParam = params.get("letters");
  if (lettersParam) {
    var letters = lettersParam.split(",").filter(isValidLetter);
    activeFilters.letters = letters;
    letters.forEach(function (l) {
      var chip = document.querySelector(
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
    var singleLetter = params.get("letter");
    activeFilters.letters = [singleLetter];
    var chip = document.querySelector(
      '.letter-chip[data-letter="' + singleLetter + '"]',
    );
    if (chip) {
      chip.classList.add("active");
      chip.setAttribute("aria-pressed", "true");
    }
  }

  // Boolean toggles
  ["biblical", "unisex", "palindrome", "alliteration"].forEach(function (key) {
    if (params.get(key)) {
      activeFilters[key] = true;
      var btn = document.querySelector(
        '.filter-toggle[data-filter="' + key + '"]',
      );
      if (btn) {
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
      }
    }
  });
}

// Save state whenever filters change
var origApplyFilters = applyFilters;
applyFilters = function () {
  origApplyFilters();
  saveStateToHash();
};

// Load state on startup, then load data
loadStateFromHash();
loadData(currentGender);
