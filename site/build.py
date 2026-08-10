#!/usr/bin/env python3
"""Render content/ into docs/ with pandoc. Standard library only.

Reads lessons.toml, expands <!-- include: --> directives, computes navigation,
runs pandoc once per lesson, and writes index.html, status.html, and .nojekyll.

Usage:
    python3 site/build.py [--strict] [--only ID ...]

--strict  every lesson with verify = "required" must have a green run recorded
          in verify/report.json. Use this for a release build (T30).
--only    build just these lesson ids. Everything still validates, so a broken
          manifest fails even when building one page.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"
DOCS = ROOT / "docs"
TEMPLATES = SITE / "templates"

VALID_TIERS = ("crawl", "walk", "run")
VALID_TRACKS = ("py", "r", "rust", "both")
VALID_VERIFY = ("required", "manual", "none")

INCLUDE_RE = re.compile(r"^[ \t]*<!--[ \t]*include:[ \t]*(\S+?)[ \t]*-->[ \t]*$", re.M)
# The template renders the title from lessons.toml, so a leading H1 in the
# source would give every page two of them. Ported blog posts all carry one.
LEADING_H1_RE = re.compile(r"\A(?:\s*<!--.*?-->\s*)*\s*#[ \t]+[^\n]*\n", re.S)
# Sibling posts are linked as ./name.md so the sources stay readable on GitHub.
# The published site serves .html, so those links 404 unless rewritten here.
MD_LINK_RE = re.compile(r"(\]\((?!https?://)[^)]*?)\.md(#[^)]*)?\)")
FENCE_RE = re.compile(r"^[ \t]*```+[ \t]*([A-Za-z0-9_+-]+)", re.M)
# A fragment is shared by both tracks, so it must not commit to a language.
BANNED_FRAGMENT_LANGS = {"python", "py", "r", "rust"}


def die(msg):
    print(f"build: error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"build: warning: {msg}", file=sys.stderr)


def find_pandoc():
    """pandoc is not on the default PATH here, so resolve it explicitly."""
    cand = os.environ.get("PANDOC") or shutil.which("pandoc") or "/opt/homebrew/bin/pandoc"
    if not Path(cand).is_file() or not os.access(cand, os.X_OK):
        die(
            f"pandoc not found at {cand!r}. Install it, or set PANDOC to its path. "
            "On this machine it lives at /opt/homebrew/bin/pandoc, which is not on PATH."
        )
    return cand


# --------------------------------------------------------------- manifest


def load_manifest():
    path = ROOT / "lessons.toml"
    if not path.is_file():
        die(f"missing manifest: {path}")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def validate(m):
    """Fail loudly on a manifest that would produce a broken site."""
    lessons = m.get("lesson") or []
    if not lessons:
        die("lessons.toml declares no [[lesson]] entries")

    seen = {}
    for L in lessons:
        for field in ("id", "title", "tier", "track", "order", "file", "verify"):
            if field not in L:
                die(f"lesson {L.get('id', '<no id>')!r} is missing required field {field!r}")
        lid = L["id"]
        if lid in seen:
            die(f"duplicate lesson id {lid!r}")
        seen[lid] = L
        if L["tier"] not in VALID_TIERS:
            die(f"{lid}: tier {L['tier']!r} not one of {VALID_TIERS}")
        if L["track"] not in VALID_TRACKS:
            die(f"{lid}: track {L['track']!r} not one of {VALID_TRACKS}")
        if L["verify"] not in VALID_VERIFY:
            die(f"{lid}: verify {L['verify']!r} not one of {VALID_VERIFY}")

        src = CONTENT / L["file"]
        if not src.is_file():
            die(
                f"{lid}: declared in lessons.toml but content/{L['file']} does not exist. "
                "Either write the file or remove the entry; a manifest entry without "
                "content would be an unreachable page."
            )
        # The URL mirrors the content path, so the two stay derivable from each
        # other (DESIGN.md 3.2). Enforce rather than trust.
        if Path(L["file"]).parts[0] != L["tier"]:
            die(f"{lid}: file {L['file']!r} must live under content/{L['tier']}/ to match its tier")

    # Siblings must be symmetric or the track switcher sends readers into a wall.
    for lid, L in seen.items():
        sib = L.get("sibling")
        if sib is None:
            continue
        if sib not in seen:
            die(f"{lid}: sibling {sib!r} is not a known lesson id")
        back = seen[sib].get("sibling")
        if back != lid:
            die(f"{lid}: sibling {sib!r} does not point back (it points at {back!r})")
    return seen


# ------------------------------------------------------------ include pass


# An include directive only expands when it is alone on its line. Written at
# the end of a paragraph it renders as an invisible HTML comment and the
# included content silently disappears, so catch it rather than ship a page
# with a missing section.
STRAY_INCLUDE_RE = re.compile(r"^(?!\s*<!--\s*include:).*\S.*<!--\s*include:\s*(\S+?)\s*-->", re.M)


def expand_includes(text, origin, stack=()):
    for mo in STRAY_INCLUDE_RE.finditer(text):
        line = text[: mo.start()].count("\n") + 1
        die(
            f"{origin}:{line}: include of {mo.group(1)!r} is not alone on its line, "
            "so it would be ignored and its content would vanish from the page. "
            "Put the directive on its own line."
        )

    """Expand <!-- include: path --> against content/, recursively.

    pandoc sees one flat document, so heading levels stay correct.
    """

    def sub(mo):
        rel = mo.group(1)
        frag = (CONTENT / rel).resolve()
        try:
            frag.relative_to(CONTENT.resolve())
        except ValueError:
            die(f"{origin}: include {rel!r} escapes content/")
        if not frag.is_file():
            die(f"{origin}: include {rel!r} does not exist")
        if frag in stack:
            chain = " -> ".join(str(p.relative_to(CONTENT)) for p in (*stack, frag))
            die(f"include cycle: {chain}")
        body = frag.read_text(encoding="utf-8")
        check_fragment(frag, body)
        return expand_includes(body, frag, (*stack, frag)).rstrip("\n")

    return INCLUDE_RE.sub(sub, text)


def check_fragment(path, body):
    """A _shared fragment may hold bash, never a track-specific language.

    Without this the rule erodes: someone drops a python block into a shared
    fragment and the R track silently starts shipping Python (DESIGN.md 3.4).
    """
    rel = path.relative_to(CONTENT)
    if rel.parts[0] != "_shared":
        return
    for mo in FENCE_RE.finditer(body):
        lang = mo.group(1).lower()
        if lang in BANNED_FRAGMENT_LANGS:
            line = body[: mo.start()].count("\n") + 1
            die(
                f"content/{rel}:{line}: shared fragment contains a {lang!r} code fence. "
                "Shared fragments are included into both tracks, so they may only "
                "carry language-neutral blocks such as bash. Move this into the "
                "track's own lesson file."
            )


# ------------------------------------------------------- verification state


def load_report():
    path = ROOT / "verify" / "report.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"verify/report.json is not valid JSON: {e}")
    return {r["lesson"]: r for r in data.get("runs", []) if "lesson" in r}


def verification_state(lesson, report, strict):
    """Return (badge_text, css_class). Hard-fails a recorded regression."""
    lid, policy = lesson["id"], lesson["verify"]
    rec = report.get(lid)

    if policy == "none":
        return ("Not machine-checked", "unverified")

    if policy == "manual":
        if rec and rec.get("checked_on"):
            return (f"Manually checked on {rec['checked_on']}", "manual")
        return ("Awaiting manual check", "unverified")

    if rec is None:
        # No record at all. Blocking here would deadlock the build before the
        # harness has ever run, so this is a warning by default and an error
        # under --strict, which is what a release build uses.
        msg = f"{lid}: verify = \"required\" but no run recorded in verify/report.json"
        if strict:
            die(msg + " (--strict)")
        warn(msg)
        return ("Not yet verified", "unverified")

    if not rec.get("green"):
        # A recorded failure blocks publishing but not authoring. Under
        # --strict (release) it is fatal, because shipping a known-broken
        # snippet to a reader is the thing this whole harness exists to
        # prevent. Without --strict the page still renders, carrying a red
        # badge and a status.html row naming the failure, because someone
        # fixing that lesson needs to be able to build and read it.
        msg = (f"{lid}: last verification run was RED "
               f"({rec.get('failure', 'no detail recorded')})")
        if strict:
            die(msg + " (--strict). Fix the lesson or re-run `just verify " + lid + "`.")
        warn(msg)
        return (f"Verification FAILED against AstraeaDB {rec.get('rev', '?')} "
                f"on {rec.get('date', '?')}", "red")

    return (f"Verified against AstraeaDB {rec.get('rev', '?')} on {rec.get('date', '?')}", "green")


# ------------------------------------------------------------- navigation


def track_of(lesson):
    return lesson["track"]


def visible_to(lesson, track):
    """Is this lesson shown to a reader who chose `track`?"""
    t = lesson["track"]
    return t in ("both", track) or track is None


def build_sidebar(manifest, lessons, current_id, root=""):
    """One sidebar for everyone. JS hides the other track's entries; with JS
    off both tracks show and every link still resolves (DESIGN.md 3.3)."""
    tiers = {t["name"]: t for t in manifest.get("tier", [])}
    out = ['<nav class="sidebar" aria-label="Lessons">']
    for tier_name in VALID_TIERS:
        tier = tiers.get(tier_name, {"title": tier_name.title()})
        out.append(f'<h2 class="tier">{html.escape(tier["title"])}</h2>')
        out.append("<ul>")
        for L in sorted(
            (x for x in lessons if x["tier"] == tier_name), key=lambda x: (x["order"], x["id"])
        ):
            cls = "current" if L["id"] == current_id else ""
            # root makes the link relative to the page being rendered. Without
            # it a lesson at /walk/01.html links to walk/02.html, which the
            # browser resolves as /walk/walk/02.html.
            href = root + url_for(L, from_tier=None)
            out.append(
                f'<li data-track="{L["track"]}" class="{cls}">'
                f'<a href="{href}">{html.escape(L["title"])}</a></li>'
            )
        out.append("</ul>")
    pages = [p for p in manifest.get("page", [])]
    if pages:
        out.append('<h2 class="tier">Reference</h2>')
        out.append("<ul>")
        for pg in pages:
            cls = "current" if pg["id"] == current_id else ""
            href = root + Path(pg["file"]).with_suffix(".html").as_posix()
            out.append(f'<li data-track="both" class="{cls}">'
                       f'<a href="{href}">{html.escape(pg["title"])}</a></li>')
        out.append("</ul>")
    out.append("</nav>")
    return "\n".join(out)


def url_for(lesson, from_tier=None):
    """Site-root-relative URL. The path mirrors content/ exactly."""
    stem = Path(lesson["file"]).with_suffix(".html")
    rel = f"{stem.as_posix()}"
    return ("../" if from_tier else "") + rel


def prev_next(lessons, lesson):
    """Neighbours within the reader's own track, so a Python reader never
    lands on an R page by accident (DESIGN.md 3.3)."""
    track = lesson["track"]
    if track == "both":
        peers = sorted(lessons, key=lambda x: (VALID_TIERS.index(x["tier"]), x["order"], x["id"]))
    else:
        peers = sorted(
            (x for x in lessons if x["track"] in (track, "both")),
            key=lambda x: (VALID_TIERS.index(x["tier"]), x["order"], x["id"]),
        )
    ids = [x["id"] for x in peers]
    i = ids.index(lesson["id"])
    return (peers[i - 1] if i > 0 else None, peers[i + 1] if i + 1 < len(peers) else None)


# ---------------------------------------------------------------- rendering


def render_lesson(pandoc, manifest, lessons, lesson, report, strict):
    src = CONTENT / lesson["file"]
    body = expand_includes(src.read_text(encoding="utf-8"), src)
    # Drop the source's own H1; the template supplies it from the manifest, so
    # keeping both would put two <h1> elements on every ported page.
    body = LEADING_H1_RE.sub("", body, count=1)
    body = MD_LINK_RE.sub(lambda m: f"{m.group(1)}.html{m.group(2) or ''})", body)

    badge, badge_cls = verification_state(lesson, report, strict)
    prev, nxt = prev_next(lessons, lesson)
    sib = next((x for x in lessons if x["id"] == lesson.get("sibling")), None)

    out_path = DOCS / Path(lesson["file"]).with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    site = manifest.get("site", {})
    depth = len(Path(lesson["file"]).parts) - 1
    root = "../" * depth

    argv = [
        pandoc,
        "--standalone",
        "--template", str(TEMPLATES / "lesson.html"),
        # pandoc 3.9 renamed --highlight-style to --syntax-highlighting.
        "--syntax-highlighting", "tango",
        "--toc", "--toc-depth=2",
        "--from", "gfm",
        "--to", "html5",
        "-V", f"pagetitle={lesson['title']}",
        "-V", f"sitetitle={site.get('title', '')}",
        "-V", f"tier={lesson['tier']}",
        "-V", f"track={lesson['track']}",
        "-V", f"lessonid={lesson['id']}",
        "-V", f"root={root}",
        "-V", f"repo={site.get('repo', '')}",
        "-V", f"badge={badge}",
        "-V", f"badgeclass={badge_cls}",
        "-V", f"sidebar={build_sidebar(manifest, lessons, lesson['id'], root)}",
        "-o", str(out_path),
    ]
    if sib:
        argv += ["-V", f"siblinghref={root}{url_for(sib)}", "-V", f"siblingtrack={sib['track']}"]
    if prev:
        argv += ["-V", f"prevhref={root}{url_for(prev)}", "-V", f"prevtitle={prev['title']}"]
    if nxt:
        argv += ["-V", f"nexthref={root}{url_for(nxt)}", "-V", f"nexttitle={nxt['title']}"]

    proc = subprocess.run(argv, input=body, text=True, capture_output=True)
    if proc.returncode != 0:
        die(f"pandoc failed on {lesson['id']}:\n{proc.stderr.strip()}")
    if proc.stderr.strip():
        warn(f"{lesson['id']}: {proc.stderr.strip()}")
    return out_path


def render_page(pandoc, manifest, lessons, page):
    """A standalone page: rendered with the lesson template, but with no tier,
    no track, and no place in the prev/next chain. The glossary is one."""
    src = CONTENT / page["file"]
    if not src.is_file():
        die(f"page {page['id']!r}: content/{page['file']} does not exist")
    body = expand_includes(src.read_text(encoding="utf-8"), src)
    body = LEADING_H1_RE.sub("", body, count=1)
    body = MD_LINK_RE.sub(lambda m: f"{m.group(1)}.html{m.group(2) or ''})", body)

    out_path = DOCS / Path(page["file"]).with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    depth = len(Path(page["file"]).parts) - 1
    root = "../" * depth
    site = manifest.get("site", {})

    argv = [
        pandoc, "--standalone",
        "--template", str(TEMPLATES / "lesson.html"),
        "--syntax-highlighting", "tango",
        "--from", "gfm", "--to", "html5",
        "-V", f"pagetitle={page['title']}",
        "-V", f"sitetitle={site.get('title', '')}",
        "-V", f"root={root}",
        "-V", f"repo={site.get('repo', '')}",
        "-V", "badge=Reference page, no code to verify",
        "-V", "badgeclass=unverified",
        "-V", f"sidebar={build_sidebar(manifest, lessons, page['id'], root)}",
        "-o", str(out_path),
    ]
    proc = subprocess.run(argv, input=body, text=True, capture_output=True)
    if proc.returncode != 0:
        die(f"pandoc failed on page {page['id']}:\n{proc.stderr.strip()}")


def fill(template_path, mapping):
    """Tiny {{key}} substitution. Deliberately not a template engine."""
    text = template_path.read_text(encoding="utf-8")
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", v)
    leftover = re.findall(r"\{\{(\w+)\}\}", text)
    if leftover:
        die(f"{template_path.name}: unfilled placeholders {sorted(set(leftover))}")
    return text


def render_index(manifest, lessons, report, strict):
    tiers = manifest.get("tier", [])
    site = manifest.get("site", {})
    cards = []
    for tier in tiers:
        items = sorted(
            (x for x in lessons if x["tier"] == tier["name"]), key=lambda x: (x["order"], x["id"])
        )
        if items:
            li = "\n".join(
                f'<li data-track="{L["track"]}"><a href="{url_for(L)}">{html.escape(L["title"])}</a>'
                f'<span class="tag">{L["track"]}</span></li>'
                for L in items
            )
        else:
            # An empty tier card reads as broken. Say plainly that the lessons
            # are not written yet rather than showing a blank list.
            li = '<li class="pending">These lessons are still being written.</li>'
        cards.append(
            f'<section class="tier-card" id="{tier["name"]}">'
            f'<h2>{html.escape(tier.get("title", tier["name"]))}</h2>'
            f'<p class="blurb">{html.escape(tier.get("blurb", ""))}</p>'
            f'<p class="outcome"><strong>After this tier:</strong> '
            f'{html.escape(tier.get("outcome", ""))}</p>'
            f'<p class="meta">{html.escape(tier.get("time", ""))}'
            f' &middot; {html.escape(tier.get("prereqs", ""))}</p>'
            f"<ul class=\"lesson-list\">{li}</ul></section>"
        )

    greens = [r for r in report.values() if r.get("green")]
    if greens:
        latest = max(greens, key=lambda r: r.get("date", ""))
        strip = (
            f"Every lesson on this site was last run against AstraeaDB "
            f"<code>{html.escape(str(latest.get('rev', '?')))}</code> on "
            f"{html.escape(str(latest.get('date', '?')))}."
        )
    else:
        strip = "Verification has not been run yet."

    # index.md is markdown like any other content, so it goes through pandoc as
    # a fragment. Substituting it raw would put literal markdown on the page.
    intro_path = CONTENT / "index.md"
    intro = ""
    if intro_path.is_file():
        proc = subprocess.run(
            [find_pandoc(), "--from", "gfm", "--to", "html5"],
            input=intro_path.read_text(encoding="utf-8"),
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            die(f"pandoc failed on content/index.md:\n{proc.stderr.strip()}")
        intro = proc.stdout

    body = fill(
        TEMPLATES / "index.html",
        {
            "sitetitle": html.escape(site.get("title", "")),
            "sidebar": build_sidebar(manifest, lessons, None),
            "intro": intro,
            "cards": "\n".join(cards),
            "strip": strip,
            "repo": site.get("repo", ""),
            "license": html.escape(site.get("license", "")),
            "styleguide": site.get("style_guide", ""),
            "year": str(date.today().year),
        },
    )
    (DOCS / "index.html").write_text(body, encoding="utf-8")


def render_status(manifest, lessons, report):
    rows = []
    for L in sorted(lessons, key=lambda x: (VALID_TIERS.index(x["tier"]), x["order"], x["id"])):
        rec = report.get(L["id"], {})
        if L["verify"] == "none":
            state, cls, detail = "not checked", "unverified", "Prose only, no code blocks."
        elif L["verify"] == "manual":
            state = "manual" if rec.get("checked_on") else "pending"
            cls = "manual" if rec.get("checked_on") else "unverified"
            detail = f"Checklist run {rec.get('checked_on', 'never')}."
        elif not rec:
            state, cls, detail = "not run", "unverified", "No record in verify/report.json."
        elif rec.get("green"):
            state, cls = "green", "green"
            detail = f"AstraeaDB {rec.get('rev', '?')} on {rec.get('date', '?')}"
        else:
            state, cls, detail = "red", "red", str(rec.get("failure", "unknown failure"))
        skips = rec.get("skipped") or []
        if skips:
            detail += " Skipped: " + "; ".join(
                f"{s.get('block', '?')} ({s.get('reason', 'no reason given')})" for s in skips
            )
        rows.append(
            f'<tr class="{cls}"><td><a href="{url_for(L)}">{html.escape(L["title"])}</a></td>'
            f'<td>{L["tier"]}</td><td>{L["track"]}</td>'
            f'<td class="state">{state}</td><td>{html.escape(detail)}</td></tr>'
        )
    body = fill(
        TEMPLATES / "status.html",
        {
            "sitetitle": html.escape(manifest.get("site", {}).get("title", "")),
            "sidebar": build_sidebar(manifest, lessons, None),
            "rows": "\n".join(rows),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        },
    )
    (DOCS / "status.html").write_text(body, encoding="utf-8")


def copy_static():
    for name in ("assets",):
        src = SITE / name
        if src.is_dir():
            shutil.copytree(src, DOCS / name, dirs_exist_ok=True)
    for name in ("samples", "data"):
        src = ROOT / name
        if src.is_dir() and any(src.iterdir()):
            shutil.copytree(src, DOCS / name, dirs_exist_ok=True)
    # Stops GitHub Pages running the pandoc output through Jekyll.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")


HREF_RE = re.compile(r'(?:href|src)="([^"]+)"')


def check_links():
    """Resolve every local link relative to the page it appears in.

    A link can name a file that exists and still be wrong, because the browser
    resolves it against the page's own directory. A sidebar entry of
    `walk/02.html` written into `/walk/01.html` becomes `/walk/walk/02.html`.
    Checking that the target exists is not enough; it has to be checked from
    where the link lives.
    """
    broken = []
    for page in sorted(DOCS.rglob("*.html")):
        for m in HREF_RE.finditer(page.read_text(encoding="utf-8")):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            if not path:
                continue
            resolved = (page.parent / path).resolve()
            if not resolved.exists():
                broken.append(f"{page.relative_to(DOCS)} -> {target}")
    if broken:
        die("links that do not resolve from the page they appear on:\n    "
            + "\n    ".join(broken[:20])
            + (f"\n    ... and {len(broken) - 20} more" if len(broken) > 20 else ""))
    print("build: all local links resolve")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="every verify=required lesson must have a green run")
    ap.add_argument("--only", nargs="*", default=None, help="build only these lesson ids")
    args = ap.parse_args()

    pandoc = find_pandoc()
    manifest = load_manifest()
    by_id = validate(manifest)
    lessons = list(by_id.values())
    report = load_report()

    targets = lessons
    if args.only:
        unknown = [i for i in args.only if i not in by_id]
        if unknown:
            die(f"unknown lesson id(s): {unknown}")
        targets = [by_id[i] for i in args.only]

    # Before anything is rendered: the downloadable sample projects are
    # generated from the lessons, and copy_static() publishes them. Shipping a
    # sample that no longer matches the page it came from is worse than
    # shipping no sample at all, so this is a build failure, not a warning.
    from sync_samples import sync as sync_samples
    sync_samples(manifest, check=True)

    DOCS.mkdir(exist_ok=True)
    for L in targets:
        render_lesson(pandoc, manifest, lessons, L, report, args.strict)
    for pg in manifest.get("page", []):
        render_page(pandoc, manifest, lessons, pg)

    render_index(manifest, lessons, report, args.strict)
    render_status(manifest, lessons, report)
    copy_static()

    check_links()

    big = [
        p for p in DOCS.rglob("*.html")
        if p.stat().st_size > 60 * 1024
    ]
    for p in big:
        warn(f"{p.relative_to(DOCS)} is {p.stat().st_size // 1024} KB, over the 60 KB budget")

    print(f"build: {len(targets)} lesson(s) + index + status -> {DOCS.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
