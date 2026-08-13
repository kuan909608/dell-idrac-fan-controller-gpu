#!/usr/bin/env bash

set -euo pipefail

readonly REPOSITORY="kuan909608/dell-idrac-fan-controller-gpu"
readonly VERSION="v1.1.0"
readonly TARGETDIR="${1:-/opt/fan_control}"

for command_name in curl tar; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name"
        exit 1
    fi
done

download_dir="$(mktemp -d)"
trap 'rm -rf -- "$download_dir"' EXIT

archive="$download_dir/source.tar.gz"
source_dir="$download_dir/source"
mkdir -p "$source_dir"

echo "*** Downloading $REPOSITORY $VERSION..."
curl \
    --proto '=https' \
    --tlsv1.2 \
    --fail \
    --location \
    --silent \
    --show-error \
    "https://github.com/$REPOSITORY/archive/$VERSION.tar.gz" \
    --output "$archive"

tar --extract --gzip --file "$archive" --directory "$source_dir" --strip-components=1

if [ ! -x "$source_dir/uninstall.sh" ]; then
    echo "Downloaded source archive does not contain the expected uninstaller."
    exit 1
fi

bash "$source_dir/uninstall.sh" "$TARGETDIR"
