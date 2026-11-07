#!/usr/bin/env bash
# Appends Windows, Linux and macOS desktop export presets to export_presets.cfg (existing presets stay untouched).
set -e
CFG="${1:-export_presets.cfg}"
touch "$CFG"
add() {  # name platform path options...
  local NAME="$1" PLAT="$2" OUT="$3"; shift 3
  grep -q "name=\"$NAME\"" "$CFG" && return 0
  local N; N=$(grep -cE '^\[preset\.[0-9]+\]$' "$CFG" || true)
  [ -s "$CFG" ] && [ -n "$(tail -c1 "$CFG")" ] && echo >> "$CFG"
  {
    printf '\n[preset.%s]\n\nname="%s"\nplatform="%s"\nrunnable=true\nadvanced_options=false\ndedicated_server=false\ncustom_features=""\nexport_filter="all_resources"\ninclude_filter=""\nexclude_filter="**/test_*"\nexport_path="%s"\nencryption_include_filters=""\nencryption_exclude_filters=""\nencrypt_pck=false\nencrypt_directory=false\n\n[preset.%s.options]\n\n' "$N" "$NAME" "$PLAT" "$OUT" "$N"
    for o in "$@"; do printf '%s\n' "$o"; done
  } >> "$CFG"
}
add "Windows PC" "Windows Desktop" "build/pc/SaleelAlHadid.exe" \
  'binary_format/architecture="x86_64"' 'binary_format/embed_pck=true' 'application/modify_resources=false' \
  'application/product_name="Saleel Al Hadid"' 'application/company_name="SABAK STUDIOS"'
add "Linux PC" "Linux" "build/linux/SaleelAlHadid.x86_64" \
  'binary_format/architecture="x86_64"' 'binary_format/embed_pck=true'
add "Mac" "macOS" "build/mac/SaleelAlHadid.zip" \
  'binary_format/architecture="universal"' 'application/bundle_identifier="com.sabak.saleelalhadid"' \
  'application/short_version="1.0"' 'application/version="1.0"' 'codesign/codesign=0' 'notarization/notarization=0'
echo "Desktop presets ready."
