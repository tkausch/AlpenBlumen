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

## License

Distributed under the terms of the  GPL-3.0 license License. See `LICENSE` for details.
