# PrepMI-PrepYU

Dataset Prep Studio for cutting image sheets, organizing LoRA image projects, captioning images, validating folders, tracking prep history, and preparing editable Ostris AI Toolkit YAML presets.

The app is a local PySide6 desktop application using the same GUI family and dark visual style as CutMI-CutYU.

## Run

```bat
python -m pip install -r requirements.txt
run.bat
```

## Project Defaults

Projects are user-selected or stored below:

```text
<application folder>\datasets\
```

The app creates this generic project structure. The `dataset\` folder is the project images folder; the top-level selected folder is the project.

```text
anchors\
dataset\split\
1.Prep\0.use\
1.Prep\0.useV2\
0.Prepped\
rejected\
manifest.json
```

No project path, trigger token, caption backend, or final export size is hardcoded.

## Caption Models

Caption Settings defaults local models to:

```text
<application folder>\models\
```

Use `Settings` to add other caption model locations and provider API keys. Use `Caption Settings -> Model Registry` to edit starter presets for Hugging Face, Civitai, direct URLs, GitHub, or custom local models. Registry entries include provider, repo/model ID, source URL, target folder, download command notes, and setup warnings.

## Ostris Presets

The Ostris Configs tab mirrors AI Toolkit's New Training Job layout with Job, Model, Quantize / Compile, Target, Save, Training, Dataset, and Sample sections. Model Architecture stores AI Toolkit's `model.arch` value while showing the familiar UI label, and architecture presets fill matching `model.name_or_path`, adapter path, quantization, Low VRAM, sampling, and extra-path defaults where applicable.

Job Type switches between LoRA Trainer and Concept Slider behavior. Concept Slider hides the LoRA target controls, shows the Slider controls, and writes the AI Toolkit `slider` block. Sample prompts use expandable rows with add/remove controls and serialize to `sample.samples`.
