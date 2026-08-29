#!/usr/bin/env sh
set -eu

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter is required: https://docs.flutter.dev/get-started/install" >&2
  exit 1
fi

cd "$(dirname "$0")/../mobile"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

cp pubspec.yaml "$tmp_dir/pubspec.yaml"
mkdir -p "$tmp_dir/lib"
cp lib/main.dart "$tmp_dir/lib/main.dart"

flutter create . --platforms=android,ios --project-name=scientific_translator_mobile
cp "$tmp_dir/pubspec.yaml" pubspec.yaml
cp "$tmp_dir/lib/main.dart" lib/main.dart
flutter pub get
printf '\nMobile shells generated. Run: cd mobile && flutter run\n'
