const boysUrl =
  "https://raw.githubusercontent.com/dxdc/babynames/main/boys.csv";
const girlsUrl =
  "https://raw.githubusercontent.com/dxdc/babynames/main/girls.csv";

const div = document.getElementById("wrapper");

const numericSort = (a, b) => {
  a = Number(a);
  b = Number(b);
  if (a > b) {
    return 1;
  } else if (b > a) {
    return -1;
  } else {
    return 0;
  }
};

const grid = new gridjs.Grid({
  columns: [
    {
      id: "rank",
      name: "Rank",
      formatter: (cell) => parseInt(cell, 10),
      sort: {
        compare: numericSort,
      },
    },
    {
      id: "name",
      name: "Name",
    },
    {
      id: "alt_spellings",
      name: "Variations",
      sort: false,
      width: "10%",
    },
    {
      id: "n_sum",
      name: "Sum",
      hidden: true,
    },
    {
      id: "n_percent",
      name: "Pct",
      formatter: (cell) => Number(cell).toFixed(1),
      sort: {
        compare: numericSort,
      },
    },
    {
      id: "year_min",
      name: "YrMin",
      sort: {
        compare: numericSort,
      },
    },
    {
      id: "year_max",
      name: "YrMax",
      sort: {
        compare: numericSort,
      },
    },
    {
      id: "year_pop",
      name: "YrPop",
      sort: {
        compare: numericSort,
      },
    },
    {
      id: "biblical",
      name: "Biblical",
      formatter: (cell) => `${cell == 1 ? "Y" : ""}`,
    },
    {
      id: "palindrome",
      name: "Palindrome",
      hidden: true,
    },
    {
      id: "phones",
      name: "Phones",
      hidden: true,
    },
    {
      id: "first_letter",
      name: "Letter",
      hidden: true,
    },
    {
      id: "stresses",
      name: "Stresses",
      hidden: true,
    },
    {
      id: "syllables",
      name: "Syllables",
      hidden: true,
    },
    {
      id: "alliteration_first",
      name: "Alliteration",
      hidden: true,
    },
    {
      id: "unisex",
      name: "Unisex",
      formatter: (cell) => `${cell == 1 ? "Y" : ""}`,
    },
  ],
  search: true,
  resizable: true,
  sort: true,
  pagination: { limit: 100 },
  data: [],
}).render(div);

const loadBabyNames = (gender) => {
  const isBoy = gender === "M";
  document.getElementById("toggle-gender").innerHTML = isBoy ? "Boys" : "Girls";
  const dataUrl = isBoy ? boysUrl : girlsUrl;
  grid
    .updateConfig({
      data: () => {
        return new Promise((resolve) => {
          Papa.parse(dataUrl, {
            download: true,
            headers: true,
            skipEmptyLines: true,
            complete: function (results, file) {
              const headers = results.data.shift();
              resolve(results.data);
            },
          });
        });
      },
    })
    .forceRender();
};

document.querySelectorAll("a.btn-gender").forEach((button) =>
  button.addEventListener("click", (e) => {
    e.preventDefault();
    const gender = e.currentTarget.dataset.gender;
    loadBabyNames(gender);
  }),
);

// load boys by default
loadBabyNames("M");
