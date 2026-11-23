"""Build the bilingual GitHub Pages gallery using the portfolio registry."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
from shutil import copyfile

from render_portfolio import ROOT, load_registry

CATEGORIES = {
    "workflow": ("Agent workflows", "Agent 工作流"),
    "web": ("Web interfaces", "Web 界面"),
    "model": ("Modeling", "建模"),
}
ACTIONS = {
    "live": ("Open live demo", "打开在线演示"),
    "case": ("Read live case study", "阅读在线复盘"),
    "recording": ("Watch recording", "观看演示录屏"),
    "chart": ("View result chart", "查看结果图"),
}
COPY = {
    "en": {
        "locale": "en",
        "title": "Daniel Deng · Portfolio",
        "heading": "AI workflows with human review.",
        "description": "Explore desktop and web workbenches, agent case studies, and reproducible models. Each project links to its demo, repository, and test run.",
        "nav": "Site navigation",
        "projects": "Projects",
        "skip": "Skip to projects",
        "stats": ("Public projects", "Live project demos", "Automated project tests"),
        "search": "Search projects",
        "hint": "Try evidence, logistics, or modeling",
        "category": "Filter by category",
        "all": "All projects",
        "one": "{count} project",
        "many": "{count} projects",
        "empty": "No projects match this search.",
        "clear": "Clear filters",
        "repo": "Repository",
        "tests": "tests",
        "test": "test",
        "index": "GitHub repository index",
        "other_language": "中文",
        "other_locale": "zh-CN",
    },
    "zh": {
        "locale": "zh-CN",
        "title": "Daniel Deng · 作品集",
        "heading": "让 AI 工作流<br>保留人工复核。",
        "description": "浏览桌面与 Web 工作台、Agent 工程复盘和可复现的建模项目。每个项目都提供演示、仓库和测试记录。",
        "nav": "站点导航",
        "projects": "项目",
        "skip": "跳到项目列表",
        "stats": ("公开项目", "在线演示", "自动化测试"),
        "search": "搜索项目",
        "hint": "试试证据、物流或建模",
        "category": "按类别筛选",
        "all": "全部项目",
        "one": "{count} 个项目",
        "many": "{count} 个项目",
        "empty": "没有找到匹配的项目。",
        "clear": "清除筛选",
        "repo": "仓库",
        "tests": "项测试",
        "test": "项测试",
        "index": "GitHub 仓库目录",
        "other_language": "English",
        "other_locale": "en",
    },
}


def gallery_records(data: dict) -> list[dict]:
    owner = data["owner"]
    home = f"https://github.com/{owner}/"
    records = []
    for project in data["projects"]:
        if not project.get("published", True):
            continue
        repo = f"{home}{project['id']}"
        if project["repository"] != repo:
            continue
        record = project.get("gallery")
        if not record:
            raise ValueError(f"{project['id']} is missing its gallery record")
        kind = record["kind"]
        expected_demo = (
            f"https://{owner.lower()}.github.io/{project['id']}/"
            if kind in {"live", "case"}
            else repo + "#demo"
        )
        if kind not in ACTIONS or record["category"] not in CATEGORIES or record["demo"] != expected_demo:
            raise ValueError(f"{project['id']} has an invalid gallery category or demo")
        if not re.fullmatch(re.escape(repo) + r"/actions/runs/\d+", record["ci"]):
            raise ValueError(f"{project['id']} has an invalid test run link")
        if type(record["tests"]) is not int or record["tests"] < 1:
            raise ValueError(f"{project['id']} has an invalid test count")
        for key in ("title", "title_en", "summary", "summary_en", "alt", "alt_en"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"{project['id']} has no {key}")
        if type(record["order"]) is not int:
            raise ValueError(f"{project['id']} has an invalid gallery order")
        records.append({**record, "id": project["id"], "repository": repo})
    records.sort(key=lambda project: project["order"])
    if [project["order"] for project in records] != list(range(1, len(records) + 1)):
        raise ValueError("Gallery order must start at one and contain no gaps")
    return records


def render_card(record: dict, copy: dict, lang: str, prefix: str) -> str:
    english = lang == "en"
    suffix = "_en" if english else ""
    title = escape(record["title" + suffix], quote=True)
    summary = escape(record["summary" + suffix], quote=True)
    alt = escape(record["alt" + suffix], quote=True)
    slug = record["id"]
    category = escape(CATEGORIES[record["category"]][not english])
    action = escape(ACTIONS[record["kind"]][not english])
    searchable = " ".join(
        [slug, slug.replace("-", " "), *CATEGORIES[record["category"]]]
        + [record[key] for key in ("title", "title_en", "summary", "summary_en")]
    )
    tests = f'{record["tests"]} {copy["test" if record["tests"] == 1 else "tests"]}'
    load = "eager" if record["order"] <= 3 else "lazy"
    return f'''      <article class="project" id="{slug}" data-project="{record["category"]}" data-search="{escape(searchable, quote=True)}">
        <img class="project-image" src="{prefix}images/{slug}.webp" width="768" height="432" loading="{load}" decoding="async" alt="{alt}">
        <div class="project-body">
          <p class="category">{category}</p>
          <h3>{title}</h3>
          <p class="project-description">{summary}</p>
          <div class="project-links" role="group" aria-label="{title}">
            <a class="demo-link" href="{escape(record["demo"], quote=True)}">{action}</a>
            <a href="{escape(record["repository"], quote=True)}">{copy["repo"]}</a>
            <a href="{escape(record["ci"], quote=True)}">{tests}</a>
          </div>
        </div>
      </article>'''


def render_page(records: list[dict], owner: str, lang: str) -> str:
    copy = COPY[lang]
    english = lang == "en"
    prefix = "" if english else "../"
    other_url = "zh/" if english else "../"
    github = f"https://github.com/{owner}"
    metrics = (
        len(records),
        sum(p["kind"] in {"live", "case"} for p in records),
        sum(p["tests"] for p in records),
    )
    ledger = "\n".join(
        f"        <div><dt>{escape(label)}</dt><dd>{value}</dd></div>"
        for label, value in zip(copy["stats"], metrics)
    )
    filters = "\n".join(
        f'          <button type="button" data-filter="{key}" aria-pressed="{str(key == "all").lower()}">{label}</button>'
        for key, label in [("all", copy["all"]), *[(key, value[not english]) for key, value in CATEGORIES.items()]]
    )
    cards = "\n".join(render_card(record, copy, lang, prefix) for record in records)
    return f'''<!doctype html>
<html lang="{copy["locale"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(copy["description"], quote=True)}">
  <link rel="alternate" hreflang="{copy["other_locale"]}" href="{other_url}">
  <link rel="stylesheet" href="{prefix}styles.css">
  <script defer src="{prefix}filters.js"></script>
  <title>{copy["title"]}</title>
</head>
<body>
  <a class="skip" href="#projects">{copy["skip"]}</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="identity" href="./"><span class="monogram" aria-hidden="true">DD</span> Daniel Deng</a>
      <nav aria-label="{copy["nav"]}">
        <a href="#projects">{copy["projects"]}</a>
        <a href="{github}">GitHub</a>
        <a href="{other_url}" lang="{copy["other_locale"]}" hreflang="{copy["other_locale"]}">{copy["other_language"]}</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="intro" aria-labelledby="intro-heading">
      <div>
        <h1 id="intro-heading">{copy["heading"]}</h1>
        <p>{copy["description"]}</p>
      </div>
      <dl class="metrics">
{ledger}
      </dl>
    </section>
    <section class="projects" id="projects" tabindex="-1" aria-labelledby="projects-heading">
      <h2 id="projects-heading">{copy["projects"]}</h2>
      <form class="toolbar" role="search" hidden>
        <div class="search">
          <label for="project-search">{copy["search"]}</label>
          <input type="search" id="project-search" placeholder="{copy["hint"]}" spellcheck="false">
        </div>
        <div class="filters" role="group" aria-label="{copy["category"]}">
{filters}
        </div>
      </form>
      <p id="result-count" class="result-count" role="status" data-one="{copy["one"]}" data-many="{copy["many"]}">{copy["many"].replace("{count}", str(len(records)))}</p>
      <div id="empty-results" class="empty" hidden>
        <p>{copy["empty"]}</p>
        <button type="button" id="clear-filters" class="reset">{copy["clear"]}</button>
      </div>
      <div class="cards">
{cards}
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="wrap footer-inner">
      <span>Daniel Deng</span>
      <a href="{github}/portfolio">{copy["index"]}</a>
    </div>
  </footer>
</body>
</html>
'''


def build(output: Path) -> None:
    data = load_registry(ROOT)
    records = gallery_records(data)
    if not records:
        raise ValueError("Nothing to publish")
    source = ROOT / "site"
    (output / "images").mkdir(parents=True, exist_ok=True)
    (output / "zh").mkdir(exist_ok=True)
    for name in ("styles.css", "filters.js"):
        copyfile(source / name, output / name)
    for record in records:
        asset = f"images/{record['id']}.webp"
        copyfile(source / asset, output / asset)
    for lang, name in (("en", "index.html"), ("zh", "zh/index.html")):
        (output / name).write_text(render_page(records, data["owner"], lang), encoding="utf-8", newline="\n")
    print(f"Built {len(records)} public projects in English and Chinese")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=ROOT / "build/gallery")
    build(parser.parse_args().output)
