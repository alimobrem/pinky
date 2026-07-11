#!/usr/bin/env bash
set -euo pipefail

# Generate SBOM in CycloneDX format using syft
# Usage: ./generate-sbom.sh <image-or-path> [output-dir]

TARGET="${1:-.}"
OUTPUT_DIR="${2:-./sbom-output}"

mkdir -p "${OUTPUT_DIR}"

TIMESTAMP=$(date -u +%Y%m%d%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/sbom-${TIMESTAMP}.cdx.json"

echo "Generating SBOM for: ${TARGET}"
echo "Output: ${OUTPUT_FILE}"

if ! command -v syft &>/dev/null; then
    echo "ERROR: syft is not installed. Install from https://github.com/anchore/syft" >&2
    exit 1
fi

syft "${TARGET}" -o cyclonedx-json="${OUTPUT_FILE}"

echo "SBOM generated: ${OUTPUT_FILE}"
