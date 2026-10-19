#!/usr/bin/env bash
# Eén meting voor deelvraag 1: één generator met zijn scanner, op één image, met lege caches.
# Gebruik: meet.sh <trivy|syft|syft-sbom> <map met img.tar> <uitmap>
# Schrijft sbom.json, scan.json en meting.json in de uitmap. De tool-images staan al lokaal, dus ophalen telt niet mee.
set -u
VARIANT=$1 IN=$2 OUT=$3
mkdir -p "$OUT"

# Milliseconden; de duur van een stap in GitHub is maar per seconde.
ms() { date +%s%3N; }

case "$VARIANT" in
  trivy)
    # Database apart, want die hangt van het netwerk af; daarna scant Trivy zonder bij te werken.
    s=$(ms); docker run --rm -v trivycache:/root/.cache "$TRIVY" image --download-db-only --quiet; db_exit=$?; db_ms=$(( $(ms) - s ))
    s=$(ms); docker run --rm -v "$IN:/in:ro" -v "$OUT:/out" -v trivycache:/root/.cache "$TRIVY" image --input /in/img.tar \
      --format cyclonedx --output /out/sbom.json --quiet; gen_exit=$?; gen_ms=$(( $(ms) - s ))
    s=$(ms); docker run --rm -v "$OUT:/out" -v trivycache:/root/.cache "$TRIVY" sbom /out/sbom.json --skip-db-update \
      --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --format json --output /out/scan.json --quiet; scan_exit=$?
    scan_ms=$(( $(ms) - s ))
    ;;
  syft | syft-sbom)
    # De sbom-cataloger leest SBOM's die al in het image staan; bij een image staat hij standaard uit.
    extra=(); [ "$VARIANT" = syft-sbom ] && extra=(--select-catalogers +sbom-cataloger)
    s=$(ms); docker run --rm -v "$IN:/in:ro" -v "$OUT:/out" "$SYFT" docker-archive:/in/img.tar "${extra[@]}" \
      -o cyclonedx-json=/out/sbom.json -q; gen_exit=$?; gen_ms=$(( $(ms) - s ))
    s=$(ms); docker run --rm -v grypecache:/cache -e GRYPE_DB_CACHE_DIR=/cache "$GRYPE" db update -q; db_exit=$?; db_ms=$(( $(ms) - s ))
    s=$(ms); docker run --rm -v "$OUT:/out" -v grypecache:/cache -e GRYPE_DB_CACHE_DIR=/cache -e GRYPE_DB_AUTO_UPDATE=false \
      "$GRYPE" sbom:/out/sbom.json --only-fixed --fail-on high -o json --file /out/scan.json -q; scan_exit=$?
    scan_ms=$(( $(ms) - s ))
    ;;
  *) echo "onbekende variant: $VARIANT" >&2; exit 2 ;;
esac

python3 "$(dirname "$0")/tel.py" "$OUT" "$VARIANT" "$db_ms" "$db_exit" "$gen_ms" "$gen_exit" "$scan_ms" "$scan_exit"
