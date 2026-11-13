#!/usr/bin/env bash
# Download the exact PatentsView input files used for this analysis and verify their checksums.
#
# PatentsView's original public bucket (s3.amazonaws.com/data.patentsview.org) now returns 403,
# and the data has moved to the USPTO Open Data Portal (data.uspto.gov), which requires a personal
# API key. The identical April-2025 release files are preserved by the Internet Archive; the
# timestamps below pin the exact captures used. (`id_` returns the raw file without Wayback rewriting.)
#
# Total download ~753 MB (unzipped ~2.6 GB; the script never unzips to disk).
set -euo pipefail
DEST="${1:-data}"
mkdir -p "$DEST"
cd "$DEST"

BASE="https://s3.amazonaws.com/data.patentsview.org/download"
fetch () {  # $1 = wayback timestamp, $2 = file stem
  if [ ! -f "$2.tsv.zip" ]; then
    echo "Downloading $2 ..."
    curl -L --retry 3 --fail -o "$2.tsv.zip" "https://web.archive.org/web/${1}id_/${BASE}/$2.tsv.zip"
  fi
}
fetch 20250506204534 g_location_disambiguated   #   2,625,477 bytes
fetch 20250506204540 g_application              #  69,355,196 bytes
fetch 20250506204511 g_inventor_disambiguated   # 681,332,582 bytes

echo "Verifying checksums ..."
shasum -a 256 -c ../checksums.sha256
