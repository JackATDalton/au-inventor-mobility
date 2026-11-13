# Australian inventor mobility, 1976–2024 (USPTO PatentsView)

A small, fully reproducible analysis of how many Australian inventors patent abroad, and where they go. It uses the USPTO's disambiguated inventor data. It updates the 2001–10 figures in Miguelez & Fink (2013), which cannot be extended past 2012 (see [Why not just update the WIPO data?](#why-not-just-update-the-wipo-data)).

**Status:** unpublished, not peer-reviewed. Written as background research for a policy essay. Please cite as an indicative analysis and read the [limitations](#limitations).

## Headline results

Share of Australian-origin inventors whose latest patent in the window lists a non-Australian address (`out/windows.csv`):

| Window | AU-resident inventors | Immigrants¹ | AU-origin abroad | **Emigration rate** | Diaspora in US |
|---|---|---|---|---|---|
| 1981–90 | 4,195 | 305 | 303 | **6.7%** | 54% |
| 1991–2000 | 7,693 | 856 | 820 | **9.6%** | 64% |
| 2001–10 | 12,032 | 1,734 | 1,423 | **10.6%** | 61% |
| 2011–20 | 16,123 | 2,809 | 2,501 | **13.4%** | 59% |
| 2016–20 | 10,780 | 2,046 | 1,881 | **14.9%** | 60% |
| 2021–24² | 3,899 | 830 | 966 | (19.9%) | 63% |

¹ Inventors resident in Australia whose first patent lists a foreign address.
² Right-truncated: many 2021–24 filings were still pending at the data cut. **Do not interpret.**

- **Gross flows:** gross moves out of and into Australia are roughly balanced in every five-year period since the 1990s, e.g. 2016–20: 2,800 out, 2,926 in (`out/moves_by_year.csv`).
- **Destinations, 2011–20:** US 2,955; UK 612; China 397; Canada 176; Germany 136 (`out/out_destinations.csv`).
- **Calibration:** the 2001–10 rate (10.6%, people) is close to WIPO's published 12.5% for the same decade. WIPO counts inventor-patent records and identifies Australians by nationality.

## Replicate

Requirements:
- `bash`, `curl`, `unzip`, `shasum`;
- Python ≥ 3.9 (standard library only, no pandas);
- about 750 MB of free disk, 2 GB of RAM, and about 10 minutes.

```bash
git clone https://github.com/JackATDalton/au-inventor-mobility.git
cd au-inventor-mobility
bash fetch_data.sh data            # downloads 3 files (~753 MB) and verifies SHA-256
python3 -I inventor_mobility.py data out
```

The `out/` files in this repository were produced by exactly these commands. They ran on macOS 26.5.1 with Python 3.14.5 and UnZip 6.00, on 11 November 2026. `out/run_log.txt` is the console log of that run. Re-running reproduces the outputs byte for byte; the analysis contains no randomness.

### Input data

The input is the PatentsView "granted patent" tables, from the release dated 18 April 2025 (file timestamps inside the zips):

| File | Bytes (zip) | Bytes (unzipped) | Columns used |
|---|---|---|---|
| `g_inventor_disambiguated.tsv.zip` | 681,332,582 | 2,212,203,352 | `patent_id`, `inventor_id`, `location_id` |
| `g_location_disambiguated.tsv.zip` | 2,625,477 | 9,296,723 | `location_id`, `disambig_country` |
| `g_application.tsv.zip` | 69,355,196 | 423,429,117 | `patent_id`, `filing_date` |

SHA-256 checksums are in `checksums.sha256`.

**Where the files come from:**
- PatentsView's public bucket (`s3.amazonaws.com/data.patentsview.org/download/…`) returned HTTP 403 as of November 2026. PatentsView has moved to the USPTO Open Data Portal (`data.uspto.gov`), whose API needs a personal key.
- `fetch_data.sh` therefore downloads the identical files from Internet Archive captures of the original bucket, taken on 6 May 2025 (timestamps `20250506204511`, `…534`, `…540`).
- If you have Open Data Portal access, the same April-2025 release from there should give identical checksums. I did not test this.
- Location IDs differ between PatentsView releases. **Use all three files from the same release.**

## Method

Everything is in `inventor_mobility.py` (about 200 lines, standard library only).

1. **Australian locations.** Every `location_id` whose `disambig_country == "AU"` (1,368 IDs).
2. **Relevant inventors.** Stream `g_inventor_disambiguated` once and collect every `inventor_id` that ever appears with an Australian location: 39,482 inventors. Stream it a second time and keep *all* rows for those inventors, including their non-Australian patents: 259,513 inventor-patent rows.
3. **Dates.** Join each `patent_id` to its US application `filing_date` from `g_application`.
   - A few raw dates have a mistyped century (e.g. `1074-08-14`). A leading `10` is rewritten to `19`.
   - Dates outside 1950–2029 are discarded.
   - Rows without a valid date or country are dropped: 982 rows (0.4%).
   - Each inventor's rows are then sorted by filing date. The latest filing date in the sample is 8 Nov 2024.
4. **Australian-origin (proxy for nationality).** An inventor is Australian-origin if their **earliest-filed** patent lists an Australian address: 31,726 inventors.
5. **Window measures**, for each window W of filing years. An inventor's location in W is the country on their **last** patent filed in W.
   - `residents` = inventors located in Australia in W.
   - `immigrants` = residents whose first-ever patent was outside Australia.
   - `diaspora` = Australian-origin inventors located outside Australia in W.
   - `em_rate = diaspora / (residents + diaspora)`. This is the same formula as Miguelez & Fink (2013, p.12). The denominator includes immigrants, as theirs does.
6. **Move events.** For each inventor, every pair of consecutive patents where the country changes from Australia to another country (an outflow) or from another country to Australia (an inflow). A move is dated by the filing year of the first patent at the new address. One inventor can generate several moves.
7. **Leavers vs stayers** (`out/productivity.csv`): patent counts for Australian-origin inventors, by first-patent cohort and by whether they ever patented abroad. ⚠️ This comparison is **mechanically biased**: a move can only be detected for inventors with at least two patents. It is reported for completeness and should not be read as a performance result. The `mean_patents_before_first_foreign` column (about 2.0–2.8 for leavers, vs 2.3–3.8 lifetime for stayers) is the least biased of its columns.

## Why not just update the WIPO data?

**Miguelez E & Fink C (2013), *Measuring the international mobility of inventors: A new database*, WIPO Economics & Statistics Working Paper No. 8.**

- Their database identifies migrant inventors using the **nationality and residence** fields of PCT applications. These were recorded because US procedure required every inventor to be listed as an applicant.
- The America Invents Act removed that requirement from 16 September 2012. After that, PCT records largely stop recording inventor nationality (pp.9–11). Their method therefore cannot be extended past 2012.

Their published Australian figures, checked against the PDF:

| | 1991–2000 (Table 3) | 2001–10 (Table 4) |
|---|---|---|
| Australians resident abroad | 1,224 | 5,631 |
| Foreign nationals resident in Australia | 2,051 | 4,427 |
| Residents of Australia (all) | 18,842 | 39,515 |
| Emigration rate (derived) | 6.1% | 12.5% |
| Australia → US corridor | 569 (Table 5) | 3,241 (Table 6) |

**How their counts differ from this analysis:**
- Their counts are **inventor-patent records** ("unique combinations of patent numbers and names"), not individual people.
- This analysis counts **people**, using PatentsView's inventor disambiguation.

## Limitations

- **Nationality proxy.** Defining "Australian" by the first patent's address has two biases:
  - It **misses** Australians who left before their first patent (e.g. after a US PhD). That undercounts the diaspora, probably substantially.
  - It **counts as immigrants** Australians whose first patent was filed abroad and who later returned.
  - Net figures are therefore **not** a nationality balance. The *trend* in the emigration rate is the more robust quantity.
- **US-granted patents only.** Inventors who never obtain a US patent are invisible, and US destinations may be over-represented.
- **Grant lag.** Only granted patents appear. Recent filing years are incomplete (severely so for 2021–24), and 2016–20 is slightly affected.
- **Disambiguation.** PatentsView's inventor disambiguation is imperfect. Split or merged identities can create spurious moves, or hide real ones.
- **Location ≠ residence.** The address on a patent is usually, but not always, the inventor's home.
- **Patenting ≠ innovation.** Patents measure inventors who file in the US, which skews towards firms that do so.

## Repository contents

```
fetch_data.sh          download + checksum verification
checksums.sha256       SHA-256 of the three input zips
inventor_mobility.py   the full analysis
out/windows.csv        window stock measures (table above)
out/moves_by_year.csv  outflow/inflow move events by filing year
out/out_destinations.csv  top destinations of outflows, by period
out/productivity.csv   leavers vs stayers patent counts (biased; see Method step 7)
out/meta.json          sample sizes, dropped rows, max filing date
out/run_log.txt        console log of the run that produced out/
```

## Implementation notes (for anyone modifying the code)

- An earlier pandas version (pandas 3.0.4 on Python 3.14.5, macOS) crashed with a bus error (SIGBUS) inside `DataFrame.dropna` on a 259k-row frame. Setting `future.infer_string=False` did not fix it. The analysis was therefore rewritten in plain Python. The results do not depend on that history.
- The 2.2 GB inventor file is streamed through `unzip -p`, never unzipped to disk or loaded whole.
- Running from a cloud-synced folder (OneDrive) produced silent exits. Run from a local directory.

## Licence

Code: MIT (see `LICENSE`).
- PatentsView data are public-domain USPTO data. Cite PatentsView (https://patentsview.org) and the USPTO.
- The output CSVs are derived aggregates, released under CC BY 4.0.
