const toolbar = document.querySelector(".toolbar");
const search = document.getElementById("project-search");
const choices = Array.from(document.querySelectorAll("[data-filter]"));
const projects = Array.from(document.querySelectorAll("[data-project]"));
const status = document.getElementById("result-count");
const empty = document.getElementById("empty-results");
const reset = document.getElementById("clear-filters");

const normalize = value => value.normalize("NFKC").toLocaleLowerCase(document.documentElement.lang);
const records = projects.map(project => ({
  project,
  haystack: normalize(project.dataset.search),
}));
let currentCategory = "all";

function render() {
  const terms = normalize(search.value).trim().split(/\s+/).filter(Boolean);
  let visibleCount = 0;
  for (const { project, haystack } of records) {
    const inCategory = currentCategory === "all" || project.dataset.project === currentCategory;
    const matches = inCategory && terms.every(term => haystack.includes(term));
    project.hidden = !matches;
    if (matches) visibleCount += 1;
  }
  status.textContent = (visibleCount === 1 ? status.dataset.one : status.dataset.many)
    .replace("{count}", visibleCount);
  empty.hidden = visibleCount !== 0;
  for (const choice of choices) {
    choice.setAttribute("aria-pressed", String(choice.dataset.filter === currentCategory));
  }
}

for (const choice of choices) {
  choice.addEventListener("click", () => {
    currentCategory = choice.dataset.filter;
    render();
  });
}
search.addEventListener("input", render);
toolbar.addEventListener("submit", event => event.preventDefault());
reset.addEventListener("click", () => {
  search.value = "";
  currentCategory = "all";
  render();
  search.focus();
});
toolbar.hidden = false;
render();
