// Baby Names - Grid.js (Tabulator-based)
// Loads CSV data and renders with filtering, sorting, virtual scrolling

const DATA_URLS = {
  M: "boys.csv",
  F: "girls.csv",
};

let allData = [];
let table = null;
let currentGender = "M";
let activeFilters = {
  letter: null,
  biblical: false,
  unisex: false,
};

// ---------------------------------------------------------------
// Table setup
// ---------------------------------------------------------------

function initTable() {
  table = new Tabulator("#table-container", {
    height: "70vh",
    data: [],
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
        title: "Pct",
        field: "cumulative_pct",
        sorter: "number",
        width: 70,
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
        field: "alliteration_first",
        headerFilter: false,
        visible: false,
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
}

// ---------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------

function loadData(gender) {
  currentGender = gender;
  const url = DATA_URLS[gender];

  document.getElementById("loading").style.display = "block";

  Papa.parse(url, {
    download: true,
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: function (results) {
      allData = results.data;
      document.getElementById("loading").style.display = "none";

      if (!table) {
        initTable();
      }

      table.setData(allData);
      document.getElementById("total-count").textContent =
        allData.length.toLocaleString();
      applyFilters();
    },
    error: function (err) {
      document.getElementById("loading").textContent =
        "Failed to load data. Please try refreshing the page.";
    },
  });
}

// ---------------------------------------------------------------
// Filtering
// ---------------------------------------------------------------

function applyFilters() {
  if (!table) return;

  const filters = [];

  // Name search (case-insensitive via custom function)
  const search = document.getElementById("name-search").value.trim();
  if (search) {
    const searchLower = search.toLowerCase();
    filters.push({
      field: "name",
      type: function (value) {
        return String(value).toLowerCase().includes(searchLower);
      },
    });
  }

  // Rank
  const rankVal = document.getElementById("rank-filter").value;
  if (rankVal) {
    filters.push({ field: "rank", type: "<=", value: Number(rankVal) });
  }

  // Syllables
  const syllVal = document.getElementById("syllable-filter").value;
  if (syllVal === "4") {
    filters.push({ field: "syllables", type: ">=", value: 4 });
  } else if (syllVal) {
    filters.push({ field: "syllables", type: "=", value: Number(syllVal) });
  }

  // Active After: name was still in use after this year (year_max >= value)
  const yearMin = document.getElementById("year-min").value;
  if (yearMin) {
    filters.push({ field: "year_max", type: ">=", value: Number(yearMin) });
  }

  // Active Before: name existed before this year (year_min <= value)
  const yearMax = document.getElementById("year-max").value;
  if (yearMax) {
    filters.push({ field: "year_min", type: "<=", value: Number(yearMax) });
  }

  // Starting letter
  if (activeFilters.letter) {
    filters.push({
      field: "first_letter",
      type: "=",
      value: activeFilters.letter,
    });
  }

  // Biblical
  if (activeFilters.biblical) {
    filters.push({ field: "biblical", type: "=", value: 1 });
  }

  // Unisex
  if (activeFilters.unisex) {
    filters.push({ field: "unisex", type: "=", value: 1 });
  }

  table.setFilter(filters);
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

// Dropdowns and number inputs
["rank-filter", "syllable-filter", "year-min", "year-max"].forEach(
  function (id) {
    document.getElementById(id).addEventListener("change", applyFilters);
    document.getElementById(id).addEventListener("input", function () {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(applyFilters, 300);
    });
  },
);

// Letter chips
(function () {
  const container = document.getElementById("letter-chips");
  for (let i = 65; i <= 90; i++) {
    const letter = String.fromCharCode(i);
    const chip = document.createElement("span");
    chip.className = "letter-chip";
    chip.textContent = letter;
    chip.dataset.letter = letter;
    chip.tabIndex = 0;
    chip.role = "button";
    chip.setAttribute("aria-label", "Filter by letter " + letter);
    chip.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        chip.click();
      }
    });
    chip.addEventListener("click", function () {
      if (activeFilters.letter === letter) {
        activeFilters.letter = null;
        chip.classList.remove("active");
      } else {
        document.querySelectorAll(".letter-chip").forEach(function (c) {
          c.classList.remove("active");
        });
        activeFilters.letter = letter;
        chip.classList.add("active");
      }
      applyFilters();
    });
    container.appendChild(chip);
  }
})();

// Toggle buttons (Biblical, Unisex)
document.querySelectorAll(".filter-toggle").forEach(function (btn) {
  btn.addEventListener("click", function () {
    const filter = btn.dataset.filter;
    activeFilters[filter] = !activeFilters[filter];
    btn.classList.toggle("active");
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
  activeFilters.letter = null;
  activeFilters.biblical = false;
  activeFilters.unisex = false;
  document
    .querySelectorAll(".letter-chip, .filter-toggle")
    .forEach(function (el) {
      el.classList.remove("active");
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
  const ymin = document.getElementById("year-min").value;
  if (ymin) params.set("ymin", ymin);
  const ymax = document.getElementById("year-max").value;
  if (ymax) params.set("ymax", ymax);
  if (activeFilters.letter) params.set("letter", activeFilters.letter);
  if (activeFilters.biblical) params.set("biblical", "1");
  if (activeFilters.unisex) params.set("unisex", "1");

  const hash = params.toString();
  history.replaceState(null, "", hash ? "#" + hash : location.pathname);
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
  if (params.get("ymin"))
    document.getElementById("year-min").value = params.get("ymin");
  if (params.get("ymax"))
    document.getElementById("year-max").value = params.get("ymax");
  if (params.get("letter")) {
    activeFilters.letter = params.get("letter");
    const chip = document.querySelector(
      `.letter-chip[data-letter="${activeFilters.letter}"]`,
    );
    if (chip) chip.classList.add("active");
  }
  if (params.get("biblical")) {
    activeFilters.biblical = true;
    document
      .querySelector('.filter-toggle[data-filter="biblical"]')
      .classList.add("active");
  }
  if (params.get("unisex")) {
    activeFilters.unisex = true;
    document
      .querySelector('.filter-toggle[data-filter="unisex"]')
      .classList.add("active");
  }
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
