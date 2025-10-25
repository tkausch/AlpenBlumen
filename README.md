# AlpenBlumen App

AlpenBlumen is a native SwiftUI reference app that celebrates alpine flora. Browse a curated catalog of mountain flowers, explore full-screen photography, switch between German, English, and French descriptions, and learn about each specimen’s taxonomic family, genus, and species.

- **Two intuitive tabs** – browse alphabetically or by plant family with smooth grouping and navigation.
- **Rich detail pages** – view localized descriptions, scientific naming, and immersive, full-screen imagery.
- **Built-in localization** – toggle instantly between `Deutsch`, `English`, and `Français`.
- **Offline-friendly content** – all flower data ships in `AlpenBlumen.json`, so the catalog loads instantly on device.

## Tech Stack

- SwiftUI & Combine (`@ObservableObject`) for a lightweight architecture.
- Local JSON bundle (`AlpenBlumen/other/AlpenBlumen.json`) decoded into strongly typed models.
- Custom styling via `Color+Extension.swift` and asset catalog entries.

## Project Layout

- `AlpenBlumen/Views` – Tab navigation, list, detail, modal full-screen image, and reusable view components.
- `AlpenBlumen/Model` – `Flower` model, localization helpers, and `LanguageSettings`.
- `AlpenBlumen/other` – App entry point and shared utilities.
- `AlpenBlumen/assets` – Flower photography and color assets referenced throughout the UI.

## Getting Started

1. Open `AlpenBlumen.xcodeproj` in Xcode.
2. Ensure the active scheme is **AlpenBlumen**.
3. Select an iOS simulator or device; the project targets iOS 18.4 by default (adjust in the project settings if you need an earlier deployment target).
4. Press **Run** (`⌘R`) to build and launch the app.

### Customizing the Catalog

- Add or update flower entries in `AlpenBlumen/other/AlpenBlumen.json`. Each record expects localized strings for English, German, and French plus taxonomic metadata.
- Drop matching image assets into the asset catalog, keeping the filename aligned with the flower’s Latin name (used as `imageName`).

## Localization

Language switching is handled by an environment-scoped `LanguageSettings` object. New locales can be added by:

1. Extending the `Language` enum (`AlpenBlumen/Model/LanguageSettings.swift`).
2. Supplying localized content in the JSON data file.
3. Adding the locale to the language picker menu in `FlowerListView`.

## Data Tooling

Python helpers live in `scripts/` to streamline catalog upkeep. Ensure Python 3.10+ is available and that you have network access for Wikimedia requests.

**1. Harvest Hartinger plates**
- `scripts/hartinger_images.py` queries Wikimedia Commons for Anton Hartinger plates and writes the metadata to `scripts/data/hartinger.json`.
  ```bash
  python3 scripts/hartinger_images.py
  # or target a custom file
  python3 scripts/hartinger_images.py --output data/custom_hartinger.json
  ```

**2. Build flower descriptions**
- `scripts/flower_wiki.py --from-hartinger` reads the Hartinger dataset, fetches multilingual Wikipedia summaries plus taxonomic data, and stores the result in `scripts/data/AlpenBlumen.json` (override with `--output` if needed).
  ```bash
  python3 scripts/flower_wiki.py --from-hartinger
  ```
- You can still fetch an individual species by Latin name:
  ```bash
  python3 scripts/flower_wiki.py "Gentiana verna"
  ```

**3. Download plate imagery**
- `scripts/hartinger_download_images.py` pulls the plate JPGs referenced in the Hartinger JSON into `scripts/images`, using the Latin name as the filename.
  ```bash
  python3 scripts/hartinger_download_images.py
  # skip already-downloaded files
  python3 scripts/hartinger_download_images.py --skip-existing
  ```

**4. Import images into the asset catalog**
- `scripts/add_images_to_assets.py` copies every JPG in `scripts/images` into `AlpenBlumen/assets/Assets.xcassets`, creating single-scale imagesets whose keys match the Latin names.
  ```bash
  python3 scripts/add_images_to_assets.py
  ```

After refreshing data and assets, rebuild the Xcode project so the new flowers appear in the app.

## License

Distributed under the terms of the  GPL-3.0 license License. See `LICENSE` for details.
