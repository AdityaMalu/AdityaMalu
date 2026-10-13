"""Draw the profile's stats card and project cards as SVGs from live GitHub data.

Runs daily in .github/workflows/refresh.yml. Locally: GITHUB_TOKEN=... python scripts/build.py
"""
import html, json, os, urllib.request
from datetime import datetime, timezone

USER = "AdityaMalu"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
SKIP_LANGS = {"Jupyter Notebook", "HTML", "CSS", "ShaderLab", "HLSL", "Smarty", "Makefile", "CMake", "Batchfile", "Shell", "Dockerfile"}
# Featured projects: repo -> (title, one-line pitch, live link label or None)
FEATURED = {
    "algoscope": ("AlgoScope", "Animated line-by-line traces of 159 DSA problems in Java, Python and C++. Paste Python and watch it run.", "Live site"),
    "machine-coding-lab": ("MachineCodingLab", "Machine-coding & LLD practice: build rate limiters, LRU caches and job queues against tests in the browser.", "Live site"),
    "java-visualizer": ("Java Visualizer", "Step-by-step visual walkthroughs of the JVM, collections, OOP patterns, concurrency and Spring.", "Live site"),
    "SpaceWarrior": ("SpaceWarrior", "A space shooter game written in Lua.", None),
    "BikeRideDetection": ("BikeRideDetection", "Android app that auto-replies by SMS while you're riding a two-wheeler.", None),
    "neetcode-submissions": ("NeetCode Submissions", "My NeetCode problem solutions, synced automatically.", None),
}
COLORS = {"Java": "#b07219", "C++": "#f34b7d", "Python": "#3572A5", "Go": "#00ADD8", "C#": "#178600", "Lua": "#5b6cff",
          "Kotlin": "#A97BFF", "Dart": "#00B4AB", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "C": "#555555"}
FONT = "'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "Consolas,'Courier New',monospace"


def gql(query):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "User-Agent": USER})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if "errors" in out:
        raise SystemExit(out["errors"])
    return out["data"]


def e(s):
    return html.escape(str(s), quote=True)


def wrap(text, width):
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur] if cur else lines


def frame(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="#0f1424" stroke="#2a3454" stroke-width="2"/>{body}</svg>\n')


def stats_card(d):
    u = d["user"]
    repos = [r for r in u["repositories"]["nodes"] if not r["isFork"]]
    stars = sum(r["stargazerCount"] for r in repos)
    year = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    # Count repos per main language (bytes would let one big Unity project drown out everything else).
    langs = {}
    for r in repos:
        names = [x["node"]["name"] for x in r["languages"]["edges"] if x["node"]["name"] not in SKIP_LANGS]
        if names:
            langs[names[0]] = langs.get(names[0], 0) + 1
    top = sorted(langs.items(), key=lambda x: -x[1])[:6]
    total = sum(n for _, n in top) or 1
    items = [("Public repos", u["repositories"]["totalCount"]), ("Stars earned", stars),
             ("Contributions (last year)", year), ("Followers", u["followers"]["totalCount"])]
    body = f'<text x="28" y="44" font-family="{FONT}" font-size="20" font-weight="700" fill="#e6eaf5">GitHub at a glance</text>'
    for i, (k, v) in enumerate(items):
        y = 84 + i * 34
        body += (f'<text x="28" y="{y}" font-family="{FONT}" font-size="15" fill="#aeb7d0">{e(k)}</text>'
                 f'<text x="300" y="{y}" font-family="{MONO}" font-size="17" font-weight="700" fill="#7d96ff" text-anchor="end">{v:,}</text>')
    body += f'<text x="350" y="44" font-family="{FONT}" font-size="20" font-weight="700" fill="#e6eaf5">Languages across my repos</text>'
    x = 350
    for n, size in top:  # stacked bar
        wpx = max(2, size / total * 420)
        body += f'<rect x="{x:.1f}" y="62" width="{wpx:.1f}" height="12" fill="{COLORS.get(n, "#7a84a3")}"/>'
        x += wpx
    body += '<rect x="350" y="62" width="420" height="12" rx="6" fill="none" stroke="#0f1424" stroke-width="3"/>'
    for i, (n, size) in enumerate(top):
        cx, cy = 350 + (i % 2) * 215, 104 + (i // 2) * 34
        body += (f'<circle cx="{cx + 6}" cy="{cy - 5}" r="6" fill="{COLORS.get(n, "#7a84a3")}"/>'
                 f'<text x="{cx + 20}" y="{cy}" font-family="{FONT}" font-size="15" fill="#e6eaf5">{e(n)}</text>'
                 f'<text x="{cx + 190}" y="{cy}" font-family="{MONO}" font-size="14" fill="#7a84a3" text-anchor="end">{size} repo{"s" if size != 1 else ""}</text>')
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    body += f'<text x="772" y="214" font-family="{FONT}" font-size="11" fill="#4a5573" text-anchor="end">updated {stamp}</text>'
    return frame(800, 230, body)


def project_card(r, title, pitch, live):
    lang = (r.get("primaryLanguage") or {}).get("name", "")
    body = f'<text x="24" y="40" font-family="{FONT}" font-size="20" font-weight="700" fill="#7d96ff">{e(title)}</text>'
    if live:
        body += (f'<rect x="{392 - 14 - len(live) * 8}" y="20" width="{len(live) * 8 + 14}" height="26" rx="13" fill="#163a30"/>'
                 f'<text x="{392 - 7 - len(live) * 4}" y="38" font-family="{FONT}" font-size="12.5" font-weight="700" fill="#5fd7a8" text-anchor="middle">{e(live)}</text>')
    for i, line in enumerate(wrap(pitch, 50)[:3]):
        body += f'<text x="24" y="{72 + i * 21}" font-family="{FONT}" font-size="14.5" fill="#aeb7d0">{e(line)}</text>'
    if lang:
        body += (f'<circle cx="30" cy="148" r="6" fill="{COLORS.get(lang, "#7a84a3")}"/>'
                 f'<text x="42" y="153" font-family="{FONT}" font-size="13.5" fill="#aeb7d0">{e(lang)}</text>')
    body += (f'<text x="392" y="153" font-family="{FONT}" font-size="13.5" fill="#aeb7d0" text-anchor="end">'
             f'★ {r["stargazerCount"]}</text>')
    return frame(416, 172, body)


def main():
    d = gql(f"""{{ user(login: "{USER}") {{
      followers {{ totalCount }}
      contributionsCollection {{ contributionCalendar {{ totalContributions }} }}
      repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {{ totalCount nodes {{
        name isFork stargazerCount primaryLanguage {{ name }}
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{ edges {{ size node {{ name }} }} }} }} }} }} }}""")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(stats_card(d))
    by_name = {r["name"]: r for r in d["user"]["repositories"]["nodes"]}
    for name, (title, pitch, live) in FEATURED.items():
        if name in by_name:
            with open(os.path.join(OUT, f"card-{name}.svg"), "w", encoding="utf-8", newline="\n") as f:
                f.write(project_card(by_name[name], title, pitch, live))
    print("wrote stats.svg and", len(FEATURED), "cards")


if __name__ == "__main__":
    main()
