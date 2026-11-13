"""Australian inventor mobility from PatentsView (USPTO granted patents, filings 1976 - early 2025).

Pure-Python (no pandas: pandas 3.0.4 on Python 3.14 bus-errored on this machine).

Method (my own; NOT the WIPO nationality method, which cannot be updated past Sept 2012):
- Unit = disambiguated inventor (PatentsView inventor_id), not inventor-patent records.
- "Australian-origin" inventor = their earliest-filed patent lists an Australian address
  (a proxy for nationality: it captures Australians who invented in Australia before leaving,
  and misses Australians who left before their first patent).
- Each inventor-patent row is dated by the US application filing date.
- Window measures (cf. Miguelez & Fink 2013, WIPO WP8, Table 4 and p.12 formula):
    residents_W  = inventors whose LAST patent in window W lists an AU address
    diaspora_W   = AU-origin inventors whose last patent in W lists a non-AU address
    immigrants_W = residents_W whose first-ever patent was outside AU
    em_rate      = diaspora / (residents + diaspora)
- Move events: consecutive patents (by filing date) of one inventor where the country changes
  AU -> X (outflow) or X -> AU (inflow); dated by the filing year of the first patent at the new address.

Usage: python3 -I inventor_mobility.py <dir with the three PatentsView zips> <outdir>
Inputs (PatentsView release of Apr 2025, retrieved via Internet Archive capture of 6 May 2025):
  g_inventor_disambiguated.tsv.zip, g_location_disambiguated.tsv.zip, g_application.tsv.zip
"""
import sys, os, json, csv, subprocess, re, statistics
from collections import defaultdict, Counter

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
csv.field_size_limit(10**8)


def stream(zname, cols):
    p = subprocess.Popen(["unzip", "-p", f"{src}/{zname}"], stdout=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace", bufsize=1 << 20)
    r = csv.reader(p.stdout, delimiter="\t")
    hdr = next(r)
    idx = [hdr.index(c) for c in cols]
    for row in r:
        if len(row) == len(hdr):
            yield [row[i] for i in idx]
    p.wait()


loc_country = {lid: c for lid, c in stream("g_location_disambiguated.tsv.zip", ["location_id", "disambig_country"])}
au_locs = {l for l, c in loc_country.items() if c == "AU"}
print("AU location ids:", len(au_locs), flush=True)

inv_cols = ["patent_id", "inventor_id", "location_id"]
ever_au = {iid for pid, iid, lid in stream("g_inventor_disambiguated.tsv.zip", inv_cols) if lid in au_locs}
print("inventors ever with AU address:", len(ever_au), flush=True)
rows = [r for r in stream("g_inventor_disambiguated.tsv.zip", inv_cols) if r[1] in ever_au]
pids = {r[0] for r in rows}
print("inventor-patent rows for them:", len(rows), flush=True)

fdate = {}
for pid, fd in stream("g_application.tsv.zip", ["patent_id", "filing_date"]):
    if pid in pids and pid not in fdate:
        fd = re.sub(r"^10(\d\d)-", r"19\1-", fd)  # a few raw dates have typo'd centuries
        if re.match(r"^(19[5-9]\d|20[0-2]\d)-\d\d-\d\d$", fd):
            fdate[pid] = fd

by_inv = defaultdict(list)
dropped = 0
for pid, iid, lid in rows:
    c = loc_country.get(lid)
    d = fdate.get(pid)
    if not c or not d:
        dropped += 1
        continue
    by_inv[iid].append((d, pid, c))
for v in by_inv.values():
    v.sort()
print("dropped rows (no date/country):", dropped, flush=True)

origin = {i: v[0][2] for i, v in by_inv.items()}
au_origin = {i for i, c in origin.items() if c == "AU"}
max_date = max(d for v in by_inv.values() for d, _, _ in v)

# ---- window stock measures
windows = [(1981, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2011, 2015), (2016, 2020), (2021, 2024)]
win_rows = []
for a, b in windows:
    res = imm = dia = dia_us = 0
    dest = Counter()
    for i, v in by_inv.items():
        inw = [x for x in v if a <= int(x[0][:4]) <= b]
        if not inw:
            continue
        last_c = inw[-1][2]
        if last_c == "AU":
            res += 1
            imm += origin[i] != "AU"
        elif i in au_origin:
            dia += 1
            dest[last_c] += 1
    win_rows.append(dict(window=f"{a}-{b}", residents=res, immigrants=imm, diaspora=dia,
                         net=imm - dia, em_rate=round(100 * dia / (res + dia), 2),
                         imm_rate=round(100 * imm / res, 2),
                         diaspora_US=dest["US"], diaspora_US_share=round(100 * dest["US"] / dia, 1) if dia else None,
                         top_dest="; ".join(f"{k} {n}" for k, n in dest.most_common(6))))
with open(f"{out}/windows.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(win_rows[0]))
    w.writeheader(); w.writerows(win_rows)
print("\nWINDOWS")
for r in win_rows:
    print(r)

# ---- move events
outm = Counter(); inm = Counter(); out_us = Counter(); in_ret = Counter()
dest_p = defaultdict(Counter)
def period(y):
    return "1976-90" if y <= 1990 else "1991-2000" if y <= 2000 else "2001-10" if y <= 2010 else "2011-20" if y <= 2020 else "2021-24"
for i, v in by_inv.items():
    for (d0, _, c0), (d1, _, c1) in zip(v, v[1:]):
        if c0 == c1:
            continue
        y = int(d1[:4])
        if c0 == "AU":
            outm[y] += 1; dest_p[period(y)][c1] += 1
            out_us[y] += c1 == "US"
        elif c1 == "AU":
            inm[y] += 1
            in_ret[y] += i in au_origin
years = sorted(set(outm) | set(inm))
with open(f"{out}/moves_by_year.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["year", "out_moves", "out_to_US", "in_moves", "in_returning_AU_origin", "net"])
    for y in years:
        w.writerow([y, outm[y], out_us[y], inm[y], in_ret[y], inm[y] - outm[y]])
print("\nMOVES BY 5-YR (out, out_to_US, in, in_returning, net)")
for a in range(1976, 2025, 5):
    ys = range(a, min(a + 5, 2025))
    o = sum(outm[y] for y in ys); u = sum(out_us[y] for y in ys); n = sum(inm[y] for y in ys); r = sum(in_ret[y] for y in ys)
    print(f"{a}-{ys[-1]}", o, u, n, r, n - o)
with open(f"{out}/out_destinations.csv", "w", newline="") as f:
    w = csv.writer(f); ps = ["1976-90", "1991-2000", "2001-10", "2011-20", "2021-24"]
    w.writerow(["country"] + ps)
    tot = Counter()
    for p in ps:
        tot.update(dest_p[p])
    for c, _ in tot.most_common(12):
        w.writerow([c] + [dest_p[p][c] for p in ps])
print("\nOUT DESTINATIONS by period:", {p: dest_p[p].most_common(5) for p in dest_p})

# ---- productivity of AU-origin inventors: leavers vs stayers
def cohort(y):
    return "1976-90" if y <= 1990 else "1991-2000" if y <= 2000 else "2001-10" if y <= 2010 else "2011+"
grp = defaultdict(list)
for i in au_origin:
    v = by_inv[i]
    n_pat = len({p for _, p, _ in v})
    ever_abroad = any(c != "AU" for _, _, c in v)
    pre = 0
    for _, _, c in v:
        if c != "AU":
            break
        pre += 1
    grp[(cohort(int(v[0][0][:4])), ever_abroad)].append((n_pat, pre))
prod = []
for (co, ab), L in sorted(grp.items()):
    ns = [x[0] for x in L]; pre = [x[1] for x in L]
    prod.append(dict(cohort=co, ever_abroad=ab, n=len(L), mean_patents=round(statistics.mean(ns), 2),
                     median_patents=statistics.median(ns), share_5plus=round(sum(x >= 5 for x in ns) / len(ns), 3),
                     mean_patents_before_first_foreign=round(statistics.mean(pre), 2)))
with open(f"{out}/productivity.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(prod[0])); w.writeheader(); w.writerows(prod)
print("\nPRODUCTIVITY")
for r in prod:
    print(r)

json.dump(dict(au_locations=len(au_locs), inventors_ever_au=len(ever_au), inventors_with_data=len(by_inv),
               au_origin=len(au_origin), rows=len(rows), dropped=dropped, max_filing=max_date),
          open(f"{out}/meta.json", "w"), indent=1)
print("\nMETA", open(f"{out}/meta.json").read())
