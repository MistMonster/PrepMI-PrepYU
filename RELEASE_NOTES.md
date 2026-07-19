# PrepMI-PrepYU - Dataset Prep Studio

First compiled release of PrepMI-PrepYU, a local GUI tool for preparing image datasets for LoRA training and generating editable Ostris / AI Toolkit config presets.

## Highlights

- Cut / Split tools for grid sheets, face crops, and manual crop boxes
- Dataset Prep workflow for reviewing, sorting, captioning, validating, and exporting projects
- Library view with manifest preview, cached thumbnails, and large strict-set preview
- Ostris / AI Toolkit preset editor with form controls plus raw YAML editing
- User-configurable project folder structure
- Guide tab with current app screenshots
- Local-first workflow with no hardcoded dataset roots or trigger tokens

## New In This Build

- First `User` tab for folder-structure preferences
- Configurable paths for project images, split output, broad set, strict set, rejected images, anchors, and final export
- Side-by-side Dataset Prep anchor comparison
- Updated app icon applied to the window and compiled `.exe`
- Updated Guide screenshots
- Project delete safety: the app refuses to delete folders outside configured project roots
- Clean PyInstaller build with bundled assets and icon

## Distribution

Download the zip, extract it, then run:

```text
PrepMI-PrepYU.exe
```

Do not run the executable from inside the zip. Extract the full folder first so `_internal` stays next to the `.exe`.

## Included Build

- Windows compiled app
- One-folder PyInstaller distribution
- App executable: `PrepMI-PrepYU.exe`
- Required runtime files in `_internal`

## Notes

- On first launch, the app creates local folders such as `datasets`, `models`, `thumbnail_cache`, and `settings.json` next to the executable.
- No local caption models are bundled.
- API keys, model paths, and custom dataset roots are user-configured locally.
