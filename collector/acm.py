#!/usr/bin/env python3
"""Fetch the ACM-published architecture proceedings that IEEE Xplore does not carry.

ASPLOS (every year) and ISCA (the years ACM publishes it; the IEEE years come through
adc-census) are listed from Crossref and completed with abstracts and affiliations from
OpenAlex (CC0). Records are written to cache/acm/ in the same shape as the IEEE records
that collector/build.py reads. The cache is git-ignored; abstracts are only used for
classification and never published.

Usage:
  python3 collector/acm.py                 # monthly: refresh the last two years (full sweep on the first run)
  python3 collector/acm.py --full         # re-fetch every year from venues.json since_year
  python3 collector/acm.py --min-days 25  # skip if the last fetch is younger than this (cron runs it daily)

Python 3.8+, standard library only. No API key needed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "acm")
STATE = os.path.join(CACHE, "_state.json")
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venues.json")
UA = {"User-Agent": "accel-census/1.0 (https://github.com/mixedcas-lab/accel-census)"}

# (name, Crossref filter, container-title query or None, regex that accepts a returned container title, DOI prefix or None)
# ACM proceedings are not in IEEE Xplore at all. The IEEE venues below are also collected by adc-census through the
# IEEE API; until that back-catalogue sweep reaches them they are filled from Crossref/OpenAlex, and build.py drops
# these copies as soon as the IEEE record with the same DOI is in the cache.
CONFS = [
    ("ASPLOS", "International Conference on Architectural Support for Programming Languages and Operating Systems",
     re.compile(r"architectural support for programming languages", re.I), "10.1145"),
    ("ISCA", "Annual International Symposium on Computer Architecture",
     re.compile(r"international symposium on computer architecture", re.I), None),
    ("MICRO", "International Symposium on Microarchitecture",
     re.compile(r"international symposium on microarchitecture", re.I), None),
    ("HPCA", "International Symposium on High-Performance Computer Architecture",
     re.compile(r"high[- ]performance computer architecture", re.I), None),
    ("DAC", "Design Automation Conference",
     re.compile(r"^(?!.*asia).*design automation conference", re.I), None),
    ("ICCAD", "International Conference on Computer-Aided Design",
     re.compile(r"international conference on computer[- ]aided design", re.I), None),
    ("DATE", "Design, Automation and Test in Europe",
     re.compile(r"design,? automation (?:&|&amp;|and) test in europe", re.I), None),
]
JOURNALS = [("TCAD", "0278-0070"), ("TC", "0018-9340"), ("JETCAS", "2156-3357"), ("IEEE Micro", "0272-1732")]
SKIP = re.compile(r"workshop|companion|adjunct|doctoral|student research", re.I)


def log(*a):
    print("[%s]" % dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.load(r)
        except Exception as e:   # noqa: BLE001 - network hiccups: retry, then give up on this request
            if k == tries - 1:
                raise
            busy = getattr(e, "code", None) == 429          # rate limit: back off for longer
            log("  retry after", type(e).__name__, getattr(e, "code", ""))
            time.sleep((60 if busy else 5) * (k + 1))


def crossref_year(query, rx, year, prefix=None, issn=None):
    """DOIs and Crossref metadata of one year's papers of a proceedings (query + rx) or a journal (issn)."""
    out, offset = {}, 0
    while True:
        flt = "from-pub-date:%d-01-01,until-pub-date:%d-12-31" % (year, year)
        flt += (",issn:%s,type:journal-article" % issn) if issn else ",type:proceedings-article"
        if prefix:
            flt += ",prefix:" + prefix
        q = {"rows": 200, "offset": offset, "filter": flt, "select": "DOI,title,container-title,author,published,issued,page"}
        if query:
            q["query.container-title"] = query
        items = get("https://api.crossref.org/works?" + urllib.parse.urlencode(q))["message"]["items"]
        hits = 0
        for it in items:
            ct = " ".join(it.get("container-title") or [])
            if (issn or rx.search(ct)) and not SKIP.search(ct) and not (name_skip(rx) and "high-performance" in ct.lower()):
                hits += 1
                out[it["DOI"].lower()] = it
        # results are ranked by how well the container title matches: stop once a page brings nothing new
        if hits == 0 or len(items) < 200 or offset >= (3000 if issn else 1600):
            return out
        offset += 200
        time.sleep(1)


def name_skip(rx):
    """ISCA's pattern also matches HPCA's title."""
    return rx is not None and "computer architecture" in rx.pattern and "high" not in rx.pattern


def abstract_of(inv):
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


def openalex(dois):
    """OpenAlex works by DOI, 40 per request."""
    out = {}
    for i in range(0, len(dois), 40):
        chunk = dois[i:i + 40]
        q = {"filter": "doi:" + "|".join(chunk), "per_page": 50,
             "select": "doi,title,abstract_inverted_index,authorships,publication_date,publication_year"}
        for w in get("https://api.openalex.org/works?" + urllib.parse.urlencode(q, safe=":|/"))["results"]:
            out[(w.get("doi") or "").replace("https://doi.org/", "").lower()] = w
        time.sleep(0.5)
    return out


def record(name, doi, cr, oa):
    title = (oa or {}).get("title") or " ".join(cr.get("title") or [])
    ct = " ".join(cr.get("container-title") or [])
    date = (oa or {}).get("publication_date") or ""
    parts = ((cr.get("published") or cr.get("issued") or {}).get("date-parts") or [[None]])[0]
    year = (oa or {}).get("publication_year") or parts[0]
    authors = []
    if oa and oa.get("authorships"):
        for k, a in enumerate(oa["authorships"]):
            affs = [i.get("display_name") for i in a.get("institutions") or [] if i.get("display_name")]
            cc = [i.get("country_code") for i in a.get("institutions") or [] if i.get("country_code")]
            aff = ", ".join(affs[:1] + ([COUNTRY.get(cc[0], cc[0])] if cc else []))
            authors.append({"full_name": (a.get("author") or {}).get("display_name") or "", "author_order": k + 1, "affiliation": aff})
    else:
        for k, a in enumerate(cr.get("author") or []):
            authors.append({"full_name": " ".join(x for x in (a.get("given"), a.get("family")) if x), "author_order": k + 1,
                            "affiliation": "; ".join(x.get("name", "") for x in a.get("affiliation") or [])})
    return {
        "article_number": ("acm:" if doi.startswith("10.1145/") else "doi:") + doi,
        "doi": doi,
        "title": title,
        "publication_title": ct or name,
        "abstract": abstract_of((oa or {}).get("abstract_inverted_index")),
        "publication_year": year,
        "publication_date": date or (str(year) if year else ""),
        "authors": {"authors": authors},
        "content_type": "Conferences",
        "html_url": "https://doi.org/" + doi,
        "publisher": "ACM" if doi.startswith("10.1145/") else "",
    }


COUNTRY = {"US": "USA", "KR": "South Korea", "CN": "China", "TW": "Taiwan", "JP": "Japan", "DE": "Germany", "CH": "Switzerland",
           "GB": "UK", "FR": "France", "CA": "Canada", "IL": "Israel", "IN": "India", "SG": "Singapore", "NL": "Netherlands",
           "IT": "Italy", "ES": "Spain", "SE": "Sweden", "BE": "Belgium", "AU": "Australia", "HK": "Hong Kong", "GR": "Greece"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--min-days", type=int, default=0)
    ap.add_argument("--only", help="comma-separated venue names, e.g. MICRO,HPCA")
    ap.add_argument("--resume", action="store_true", help="skip venue-years already fetched in the interrupted run")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    today = dt.date.today()
    if args.min_days and state.get("last") and (today - dt.date.fromisoformat(state["last"])).days < args.min_days:
        log("ACM proceedings fetched on %s; next fetch after %d days" % (state["last"], args.min_days))
        return 0
    since = json.load(open(CONFIG)).get("since_year", 2012)
    full = args.full or not state.get("last") or bool(args.only)
    years = range(since if full else today.year - 1, today.year + 1)
    total, failed = 0, 0
    if not args.resume:
        state["done"] = []
    todo = [(n, q, rx, pre, None) for n, q, rx, pre in CONFS] + [(n, None, None, None, issn) for n, issn in JOURNALS]
    only = set(args.only.split(",")) if args.only else None
    for name, query, rx, pre, issn in todo:
        if only and name not in only:
            continue
        for y in years:
            key = "%s:%d" % (name, y)
            if args.resume and key in state.get("done", []):
                continue
            try:
                cr = crossref_year(query, rx, y, pre, issn)
                oa = openalex(sorted(cr)) if cr else {}
            except Exception as e:   # noqa: BLE001 - one failed venue-year must not stop the rest
                log("%s %d: FAILED (%s) - rerun with --resume" % (name, y, e))
                failed += 1
                continue
            if not cr:
                state.setdefault("done", []).append(key)
                continue
            for doi, it in cr.items():
                r = record(name, doi, it, oa.get(doi))
                if issn:
                    r["content_type"] = "Journals"
                if not r["title"]:
                    continue
                with open(os.path.join(CACHE, re.sub(r"[^\w.-]", "_", r["article_number"]) + ".json"), "w", encoding="utf-8") as f:
                    json.dump(r, f, ensure_ascii=False)
            n_abs = sum(1 for d in cr if (oa.get(d) or {}).get("abstract_inverted_index"))
            log("%s %d: %d papers (%d with abstracts)" % (name, y, len(cr), n_abs))
            state.setdefault("done", []).append(key)
            json.dump(state, open(STATE, "w"))
            total += len(cr)
            time.sleep(1)
    if failed:
        log("%d venue-years failed; the next run retries them" % failed)
        json.dump(state, open(STATE, "w"))
        return 1
    state["last"] = today.isoformat()
    state["done"] = []      # the next (monthly) run starts afresh
    json.dump(state, open(STATE, "w"))
    log("done: %d ACM records" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
