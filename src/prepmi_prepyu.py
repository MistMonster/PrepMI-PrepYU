from __future__ import annotations

import ctypes
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import winreg
else:  # pragma: no cover
    winreg = None

from PIL import Image, ImageChops, ImageDraw, ImageOps

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

try:
    from PySide6.QtCore import QObject, QEvent, QPoint, QProcess, QRect, QSize, Qt, QThread, Signal
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QAbstractSpinBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListView,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QSplitter,
        QStyle,
        QStyledItemDelegate,
        QStyleOptionViewItem,
        QTabWidget,
        QTextBrowser,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PySide6 is required for PrepMI-PrepYU.\n"
        "Install it with: python -m pip install -r requirements.txt"
    ) from exc


APP_NAME = "PrepMI-PrepYU"
APP_SUBTITLE = "Dataset Prep Studio"
APP_VERSION = "0.1.1"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
CAPTION_EXT = ".txt"
THEME = {
    "bg": "#101010",
    "panel": "#171717",
    "panel_alt": "#1f1f1f",
    "field": "#0f0f0f",
    "text": "#fefefe",
    "muted": "#a1a1a1",
    "accent": "#ff6363",
    "warning": "#ffb86b",
    "border": "#2a2a2a",
    "button": "#1f1f1f",
    "button_active": "#2a2a2a",
}


def built_in_theme_presets() -> dict[str, dict[str, str]]:
    return {
        "Default": dict(THEME),
        "Dracula": {"bg": "#282a36", "panel": "#343746", "panel_alt": "#3d4050", "field": "#21222c", "text": "#f8f8f2", "muted": "#b9b9c8", "accent": "#bd93f9", "warning": "#ffb86c", "border": "#44475a", "button": "#343746", "button_active": "#44475a"},
        "Nord": {"bg": "#2e3440", "panel": "#3b4252", "panel_alt": "#434c5e", "field": "#242933", "text": "#eceff4", "muted": "#d8dee9", "accent": "#88c0d0", "warning": "#ebcb8b", "border": "#4c566a", "button": "#3b4252", "button_active": "#4c566a"},
        "Tokyo Night": {"bg": "#1a1b26", "panel": "#24283b", "panel_alt": "#292e42", "field": "#16161e", "text": "#c0caf5", "muted": "#9aa5ce", "accent": "#7aa2f7", "warning": "#e0af68", "border": "#414868", "button": "#24283b", "button_active": "#343a55"},
        "One Dark": {"bg": "#21252b", "panel": "#282c34", "panel_alt": "#30343d", "field": "#1b1f27", "text": "#abb2bf", "muted": "#828997", "accent": "#61afef", "warning": "#e5c07b", "border": "#3e4451", "button": "#282c34", "button_active": "#3e4451"},
        "Solarized Dark": {"bg": "#002b36", "panel": "#073642", "panel_alt": "#0b3f4c", "field": "#00212a", "text": "#eee8d5", "muted": "#93a1a1", "accent": "#268bd2", "warning": "#b58900", "border": "#586e75", "button": "#073642", "button_active": "#124956"},
        "Solarized Light": {"bg": "#fdf6e3", "panel": "#eee8d5", "panel_alt": "#e7dfc8", "field": "#fffaf0", "text": "#073642", "muted": "#657b83", "accent": "#268bd2", "warning": "#b58900", "border": "#d6cfba", "button": "#eee8d5", "button_active": "#d6cfba"},
        "Gruvbox Dark": {"bg": "#282828", "panel": "#3c3836", "panel_alt": "#504945", "field": "#1d2021", "text": "#ebdbb2", "muted": "#bdae93", "accent": "#fabd2f", "warning": "#fe8019", "border": "#665c54", "button": "#3c3836", "button_active": "#504945"},
        "Monokai": {"bg": "#272822", "panel": "#34352d", "panel_alt": "#3e3f36", "field": "#1e1f1c", "text": "#f8f8f2", "muted": "#cfcfc2", "accent": "#a6e22e", "warning": "#fd971f", "border": "#55564d", "button": "#34352d", "button_active": "#49483e"},
        "Catppuccin Mocha": {"bg": "#1e1e2e", "panel": "#313244", "panel_alt": "#3b3d54", "field": "#181825", "text": "#cdd6f4", "muted": "#a6adc8", "accent": "#89b4fa", "warning": "#f9e2af", "border": "#45475a", "button": "#313244", "button_active": "#45475a"},
        "High Contrast Dark": {"bg": "#000000", "panel": "#111111", "panel_alt": "#191919", "field": "#050505", "text": "#ffffff", "muted": "#d0d0d0", "accent": "#00aaff", "warning": "#ffcc00", "border": "#6a6a6a", "button": "#151515", "button_active": "#252525"},
    }


def windows_color_to_hex(value: int) -> str:
    red = value & 0xFF
    green = (value >> 8) & 0xFF
    blue = (value >> 16) & 0xFF
    return f"#{red:02x}{green:02x}{blue:02x}"


def windows_theme_preset() -> dict[str, str]:
    if winreg is None:
        return dict(THEME)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            light = winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1
    except Exception:
        light = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
            accent = windows_color_to_hex(int(winreg.QueryValueEx(key, "ColorizationColor")[0]))
    except Exception:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Accent") as key:
                accent = windows_color_to_hex(int(winreg.QueryValueEx(key, "AccentColor")[0]))
        except Exception:
            accent = THEME["accent"]
    if light:
        return {"bg": "#f3f3f3", "panel": "#ffffff", "panel_alt": "#f7f7f7", "field": "#ffffff", "text": "#1f1f1f", "muted": "#5f5f5f", "accent": accent, "warning": "#9a6700", "border": "#d0d0d0", "button": "#f5f5f5", "button_active": "#e6e6e6"}
    return {"bg": "#202020", "panel": "#2b2b2b", "panel_alt": "#333333", "field": "#1b1b1b", "text": "#f3f3f3", "muted": "#b8b8b8", "accent": accent, "warning": "#ffcc66", "border": "#4a4a4a", "button": "#2d2d2d", "button_active": "#3a3a3a"}

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parents[1]
    RESOURCE_DIR = APP_DIR

DEFAULT_DATASETS_DIR = APP_DIR / "datasets"
DEFAULT_MODELS_DIR = APP_DIR / "models"
THUMB_CACHE_DIR = APP_DIR / "thumbnail_cache"
THUMB_CACHE_SIZE = 160
THUMB_CACHE_INDEX = THUMB_CACHE_DIR / "cache_index.json"
SPLIT_THUMB_TILE = 88
SPLIT_THUMB_ICON = 78
SPLIT_THUMB_SPACING = 5
SETTINGS_PATH = APP_DIR / "settings.json"
ICON_PATH = RESOURCE_DIR / "assets" / "prepmi-prepyu.ico"
GUIDE_ASSET_DIR = APP_DIR / "assets" / "guide"
DEFAULT_FOLDER_PREFERENCES = {
    "anchors": "anchors",
    "project_images": "dataset",
    "split": "dataset/split",
    "broad": "1.Prep/0.use",
    "strict": "1.Prep/0.useV2",
    "export": "0.Prepped",
    "rejected": "rejected",
}
OLD_DEFAULT_CAPTION_TEMPLATE = "<trigger>, a clear image of a <subject_type>, <framing>, <hair>, <outfit>, <setting>, <lighting>"
DEFAULT_CAPTION_TEMPLATE = "<trigger>, a clear image of a <subject_type>, <framing>, <angle>, <direction>, <expression>, <hair>, <outfit>, <setting>, <lighting>"
DEFAULT_CAPTION_PROMPT = (
    "Write exactly one concise LoRA dataset caption for this image. "
    "The caption must start with '<trigger>,' exactly. "
    "Describe only visible content. Do not mention file names, camera metadata, or uncertainty. "
    "Training target profile: <profile>. "
    "Preferred caption shape/template: <template>"
)
LOCAL_SERVER_MODEL_PRESETS = {
    "Ollama": ["qwen3.5:4b", "qwen3.5:2b", "llama3.2-vision", "gemma4", "Custom..."],
    "LM Studio": ["loaded-model", "Custom..."],
    "KoboldCPP": ["loaded-model", "Custom..."],
    "Custom OpenAI-compatible": ["loaded-model", "Custom..."],
    "Custom JSON": ["custom-vision-model", "Custom..."],
}
API_MODEL_PRESETS = {
    "OpenAI": [
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4o-mini",
        "gpt-4o",
        "Custom...",
    ],
    "Gemini": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "Custom...",
    ],
    "Anthropic": [
        "claude-3-5-haiku-latest",
        "claude-3-5-sonnet-latest",
        "claude-3-7-sonnet-latest",
        "claude-sonnet-4-0",
        "claude-opus-4-0",
        "Custom...",
    ],
    "Custom HTTP": [
        "custom-vision-model",
        "Custom...",
    ],
}
FOLDER_PREFERENCE_LABELS = {
    "anchors": "Anchor/reference images",
    "project_images": "Project images",
    "split": "Split output",
    "broad": "Broad usable set",
    "strict": "Strict training set",
    "export": "Final export",
    "rejected": "Rejected images",
}


def built_in_caption_prompt_presets() -> dict[str, str]:
    return {
        "Default LoRA Caption": DEFAULT_CAPTION_PROMPT,
    }


def all_caption_prompt_presets(settings: dict[str, Any]) -> dict[str, str]:
    presets = built_in_caption_prompt_presets()
    custom = settings.get("caption_prompt_presets", {})
    if isinstance(custom, dict):
        presets.update({str(name): str(text) for name, text in custom.items()})
    return presets


def default_caption_model_registry() -> list[dict[str, str]]:
    registry = [
        {
            "name": "Qwen3-VL 8B",
            "backend": "Qwen3-VL 8B",
            "provider": "Hugging Face",
            "repo": "Qwen/Qwen3-VL-8B-Instruct",
            "url": "https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct",
            "target_folder": str(DEFAULT_MODELS_DIR / "Qwen3-VL-8B-Instruct"),
            "download_command": "huggingface-cli download Qwen/Qwen3-VL-8B-Instruct --local-dir models/Qwen3-VL-8B-Instruct",
            "notes": "Natural-language prompt-like captioning candidate for Z-Image Base/Turbo. Large VLM; check VRAM and license before use.",
        },
        {
            "name": "Qwen3-VL 4B",
            "backend": "Qwen3-VL 4B",
            "provider": "Hugging Face",
            "repo": "Qwen/Qwen3-VL-4B-Instruct",
            "url": "https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct",
            "target_folder": str(DEFAULT_MODELS_DIR / "Qwen3-VL-4B-Instruct"),
            "download_command": "huggingface-cli download Qwen/Qwen3-VL-4B-Instruct --local-dir models/Qwen3-VL-4B-Instruct",
            "notes": "Smaller Z-Image captioning candidate. Editable preset; verify exact files and quantization preference.",
        },
        {
            "name": "Qwen3-VL 2B GGUF",
            "backend": "Qwen3-VL 2B",
            "provider": "Hugging Face",
            "repo": "Qwen/Qwen3-VL-2B-Instruct-GGUF",
            "url": "https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF",
            "target_folder": str(DEFAULT_MODELS_DIR / "Qwen3-VL-2B-Instruct-GGUF"),
            "download_command": "huggingface-cli download Qwen/Qwen3-VL-2B-Instruct-GGUF --local-dir models/Qwen3-VL-2B-Instruct-GGUF",
            "notes": "Smallest Qwen3-VL starter preset here. GGUF usually implies llama.cpp-style tooling.",
        },
        {
            "name": "JoyCaption Alpha Two",
            "backend": "JoyCaption",
            "provider": "Hugging Face",
            "repo": "fancyfeast/llama-joycaption-alpha-two-hf-llava",
            "url": "https://huggingface.co/fancyfeast/llama-joycaption-alpha-two-hf-llava",
            "target_folder": str(DEFAULT_MODELS_DIR / "llama-joycaption-alpha-two-hf-llava"),
            "download_command": "huggingface-cli download fancyfeast/llama-joycaption-alpha-two-hf-llava --local-dir models/llama-joycaption-alpha-two-hf-llava",
            "notes": "Diffusion-training caption model preset. Check upstream instructions for exact runtime dependencies.",
        },
        {
            "name": "Florence-2 Large",
            "backend": "Florence-2",
            "provider": "Hugging Face",
            "repo": "microsoft/Florence-2-large",
            "url": "https://huggingface.co/microsoft/Florence-2-large",
            "target_folder": str(DEFAULT_MODELS_DIR / "Florence-2-large"),
            "download_command": "huggingface-cli download microsoft/Florence-2-large --local-dir models/Florence-2-large",
            "notes": "General vision-language captioning and detection-capable model. Often uses Transformers with trust_remote_code.",
        },
        {
            "name": "BLIP Image Captioning Large",
            "backend": "BLIP",
            "provider": "Hugging Face",
            "repo": "Salesforce/blip-image-captioning-large",
            "url": "https://huggingface.co/Salesforce/blip-image-captioning-large",
            "target_folder": str(DEFAULT_MODELS_DIR / "blip-image-captioning-large"),
            "download_command": "huggingface-cli download Salesforce/blip-image-captioning-large --local-dir models/blip-image-captioning-large",
            "notes": "Classic image captioning baseline. Useful fallback when richer VLM captioning is not needed.",
        },
        {
            "name": "WD SwinV2 Tagger v3",
            "backend": "WD14 tagger",
            "provider": "Hugging Face",
            "repo": "SmilingWolf/wd-swinv2-tagger-v3",
            "url": "https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3",
            "target_folder": str(DEFAULT_MODELS_DIR / "wd-swinv2-tagger-v3"),
            "download_command": "huggingface-cli download SmilingWolf/wd-swinv2-tagger-v3 --local-dir models/wd-swinv2-tagger-v3",
            "notes": "Anime/tag-model captioning preset. Produces tags rather than natural prose.",
        },
        {
            "name": "Custom Civitai Caption Model",
            "backend": "Custom command",
            "provider": "Civitai",
            "repo": "",
            "url": "https://civitai.com/models",
            "target_folder": str(DEFAULT_MODELS_DIR / "civitai-custom-caption-model"),
            "download_command": "",
            "notes": "Use with a custom command or manual download. Some Civitai downloads require an API token.",
        },
    ]
    extra = [
        ("Qwen3-VL 8B Thinking", "Qwen3-VL 8B", "Qwen/Qwen3-VL-8B-Thinking", "Reasoning-oriented Qwen3-VL variant. Usually heavier/slower than Instruct for simple captioning."),
        ("Qwen3-VL 4B Thinking", "Qwen3-VL 4B", "Qwen/Qwen3-VL-4B-Thinking", "Reasoning-oriented 4B variant. Useful to compare caption detail/style against Instruct."),
        ("Qwen3-VL 4B Instruct FP8", "Qwen3-VL 4B", "Qwen/Qwen3-VL-4B-Instruct-FP8", "FP8 quantized Qwen3-VL 4B. Smaller than BF16; verify runtime support."),
        ("Qwen3-VL 4B Instruct GGUF", "Qwen3-VL 4B", "Qwen/Qwen3-VL-4B-Instruct-GGUF", "GGUF package for llama.cpp/Ollama-style local serving. Includes LLM and vision projector pieces."),
        ("Qwen3-VL 2B Instruct", "Qwen3-VL 2B", "Qwen/Qwen3-VL-2B-Instruct", "Small Qwen3-VL dense model. Better for lower VRAM; quality may be lower."),
        ("Qwen3-VL 2B Thinking", "Qwen3-VL 2B", "Qwen/Qwen3-VL-2B-Thinking", "Small reasoning-oriented Qwen3-VL variant."),
        ("Florence-2 Base", "Florence-2", "microsoft/Florence-2-base", "Smaller Florence-2 caption/detection model. Often uses Transformers with trust_remote_code."),
        ("Florence-2 Base FT", "Florence-2", "microsoft/Florence-2-base-ft", "Fine-tuned Florence-2 base variant."),
        ("Florence-2 Large FT", "Florence-2", "microsoft/Florence-2-large-ft", "Fine-tuned Florence-2 large variant."),
        ("BLIP Image Captioning Base", "BLIP", "Salesforce/blip-image-captioning-base", "Smaller classic BLIP captioning model."),
        ("WD ViT Tagger v3", "WD14 tagger", "SmilingWolf/wd-vit-tagger-v3", "Anime/tag-model preset. Produces tags rather than prose."),
        ("WD ConvNeXT Tagger v3", "WD14 tagger", "SmilingWolf/wd-convnext-tagger-v3", "Anime/tag-model preset. Produces tags rather than prose."),
        ("WD EVA02 Large Tagger v3", "WD14 tagger", "SmilingWolf/wd-eva02-large-tagger-v3", "Larger WD tagger preset. Produces tags rather than prose."),
    ]
    for name, backend, repo, notes in extra:
        folder_name = repo.split("/")[-1]
        registry.append(
            {
                "name": name,
                "backend": backend,
                "provider": "Hugging Face",
                "repo": repo,
                "url": f"https://huggingface.co/{repo}",
                "target_folder": str(DEFAULT_MODELS_DIR / folder_name),
                "download_command": f"huggingface-cli download {repo} --local-dir models/{folder_name}",
                "notes": notes,
            }
        )
    return registry


def ostris_model_arch_registry() -> list[dict[str, Any]]:
    return [
        {"arch": "zimage:turbo", "label": "Z-Image Turbo (w/ Training Adapter)", "group": "image", "name_or_path": "Tongyi-MAI/Z-Image-Turbo", "assistant_lora_path": "ostris/zimage_turbo_training_adapter/zimage_turbo_training_adapter_v2.safetensors", "low_vram": True, "qtype": "qfloat8", "sample_steps": 9, "guidance_scale": 1},
        {"arch": "zimage", "label": "Z-Image", "group": "image", "name_or_path": "Tongyi-MAI/Z-Image", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 30, "guidance_scale": 4},
        {"arch": "zimage:deturbo", "label": "Z-Image De-Turbo (De-Distilled)", "group": "image", "name_or_path": "ostris/Z-Image-De-Turbo", "extras_name_or_path": "Tongyi-MAI/Z-Image-Turbo", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 3},
        {"arch": "flux", "label": "FLUX.1", "group": "image", "name_or_path": "black-forest-labs/FLUX.1-dev", "assistant_lora_path": "", "low_vram": False, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4},
        {"arch": "flux2", "label": "FLUX.2", "group": "image", "name_or_path": "black-forest-labs/FLUX.2-dev", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4, "match_target_res": False},
        {"arch": "flux2_klein_4b", "label": "FLUX.2-klein-base-4B", "group": "image", "name_or_path": "black-forest-labs/FLUX.2-klein-base-4B", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4, "match_target_res": False},
        {"arch": "flux2_klein_9b", "label": "FLUX.2-klein-base-9B", "group": "image", "name_or_path": "black-forest-labs/FLUX.2-klein-base-9B", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4, "match_target_res": False},
        {"arch": "qwen_image", "label": "Qwen-Image", "group": "image", "name_or_path": "Qwen/Qwen-Image", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4},
        {"arch": "qwen_image:2512", "label": "Qwen-Image-2512", "group": "image", "name_or_path": "Qwen/Qwen-Image-2512", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4},
        {"arch": "qwen_image_edit", "label": "Qwen-Image-Edit", "group": "instruction", "name_or_path": "Qwen/Qwen-Image-Edit", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4},
        {"arch": "qwen_image_edit_plus", "label": "Qwen-Image-Edit-2509", "group": "instruction", "name_or_path": "Qwen/Qwen-Image-Edit-2509", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4, "match_target_res": False},
        {"arch": "qwen_image_edit_2511", "label": "Qwen-Image-Edit-2511", "group": "instruction", "name_or_path": "Qwen/Qwen-Image-Edit-2511", "assistant_lora_path": "", "low_vram": True, "qtype": "qfloat8", "sample_steps": 25, "guidance_scale": 4, "match_target_res": False},
        {"arch": "sdxl", "label": "SDXL", "group": "image", "name_or_path": "stabilityai/stable-diffusion-xl-base-1.0", "assistant_lora_path": "", "low_vram": False, "qtype": "", "sample_steps": 25, "guidance_scale": 7},
        {"arch": "sd15", "label": "SD 1.5", "group": "image", "name_or_path": "stable-diffusion-v1-5/stable-diffusion-v1-5", "assistant_lora_path": "", "low_vram": False, "qtype": "", "sample_steps": 25, "guidance_scale": 7},
        {"arch": "krea2:turbo", "label": "Krea 2 Turbo (w/ Training Adapter)", "group": "image", "name_or_path": "krea/Krea-2-Turbo", "assistant_lora_path": "ostris/krea2_turbo_training_adapter/krea2_turbo_training_adapter_v1.safetensors", "low_vram": True, "qtype": "qfloat8", "sample_steps": 9, "guidance_scale": 1},
    ]


def ostris_arch_by_value(arch: str) -> dict[str, Any]:
    for item in ostris_model_arch_registry():
        if item["arch"] == arch:
            return item
    return ostris_model_arch_registry()[0]


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def image_paths_from_items(paths: list[Path], recursive: bool = False) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            found.extend(p for p in sorted(iterator, key=lambda item: str(item).lower()) if is_image(p))
        elif is_image(path):
            found.append(path)
    return found


def open_folder(path: Path) -> None:
    if path.exists():
        os.startfile(path)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for version in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_v{version:03d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create a unique name for {path.name}")


def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def normalized_path_key(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve()).casefold()
    except Exception:
        return str(path.absolute()).casefold()


def thumbnail_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def load_thumbnail_index() -> dict[str, Any]:
    if THUMB_CACHE_INDEX.exists():
        try:
            data = json.loads(THUMB_CACHE_INDEX.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_thumbnail_index(index: dict[str, Any]) -> None:
    THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_CACHE_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")


def cached_thumbnail_path(path: Path) -> Path | None:
    if not path.exists():
        return None
    try:
        stat = path.stat()
        size = THUMB_CACHE_SIZE
        source_key = f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{size}"
        name = hashlib.sha1(source_key.encode("utf-8", errors="replace")).hexdigest() + ".jpg"
        thumb_path = THUMB_CACHE_DIR / str(size) / name
        if not thumb_path.exists():
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(path) as image:
                thumb = ImageOps.contain(image.convert("RGB"), (size, size), method=Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (size, size), (18, 18, 18))
                x = (size - thumb.width) // 2
                y = (size - thumb.height) // 2
                canvas.paste(thumb, (x, y))
                canvas.save(thumb_path, quality=88, optimize=True)
        index = load_thumbnail_index()
        index[normalized_path_key(path)] = {"source": str(path.resolve()), "thumb": str(thumb_path), **thumbnail_signature(path)}
        save_thumbnail_index(index)
        return thumb_path
    except Exception:
        return None


def cached_thumbnail_icon(path: Path, size: int = 96) -> QIcon:
    thumb_path = cached_thumbnail_path(path)
    pixmap = QPixmap(str(thumb_path or path))
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def guide_thumbnail_path(path: Path, width: int = 920) -> Path | None:
    if not path.exists():
        return None
    target = path.with_name(f"{path.stem}_thumb{path.suffix}")
    try:
        if target.exists() and target.stat().st_mtime_ns >= path.stat().st_mtime_ns:
            return target
        with Image.open(path) as image:
            ratio = width / max(1, image.width)
            thumb = image.convert("RGB").resize((width, max(1, round(image.height * ratio))), Image.Resampling.LANCZOS)
            overlay = Image.new("RGBA", thumb.size, (0, 0, 0, 0))
            badge_size = 72
            badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 165))
            badge_x = (thumb.width - badge_size) // 2
            badge_y = (thumb.height - badge_size) // 2
            overlay.paste(badge, (badge_x, badge_y))
            plus = Image.new("RGBA", thumb.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(plus)
            cx = thumb.width // 2
            cy = thumb.height // 2
            draw.line((cx - 20, cy, cx + 20, cy), fill=(255, 255, 255, 235), width=7)
            draw.line((cx, cy - 20, cx, cy + 20), fill=(255, 255, 255, 235), width=7)
            thumb_rgba = thumb.convert("RGBA")
            thumb_rgba.alpha_composite(overlay)
            thumb_rgba.alpha_composite(plus)
            thumb_rgba.convert("RGB").save(target, quality=92)
        return target
    except Exception:
        return path


def grid_boxes(width: int, height: int, rows: int, columns: int, crop: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
    left_crop, top_crop, right_crop, bottom_crop = crop
    left_bound = min(max(0, left_crop), width - 1)
    top_bound = min(max(0, top_crop), height - 1)
    right_bound = max(left_bound + 1, width - max(0, right_crop))
    bottom_bound = max(top_bound + 1, height - max(0, bottom_crop))
    work_w = right_bound - left_bound
    work_h = bottom_bound - top_bound
    boxes = []
    for row in range(max(1, rows)):
        top = top_bound + round((row / rows) * work_h)
        bottom = top_bound + round(((row + 1) / rows) * work_h)
        for column in range(max(1, columns)):
            left = left_bound + round((column / columns) * work_w)
            right = left_bound + round(((column + 1) / columns) * work_w)
            boxes.append((left, top, right, bottom))
    return boxes


def detect_grid(width: int, height: int, max_rows: int = 8, max_columns: int = 8) -> tuple[int, int]:
    aspect = width / max(1, height)
    best: tuple[float, int, int] | None = None
    for rows in range(1, max_rows + 1):
        for columns in range(1, max_columns + 1):
            if rows == 1 and columns == 1:
                continue
            cell_aspect = (width / columns) / max(1, height / rows)
            square_score = abs(cell_aspect - 1.0)
            layout_score = abs((columns / rows) - aspect)
            complexity = (rows * columns) * 0.015
            common_bonus = -0.12 if (rows, columns) in {(2, 2), (1, 2), (2, 1), (2, 3), (3, 2), (3, 3), (4, 4)} else 0
            score = square_score + layout_score * 0.35 + complexity + common_bonus
            if best is None or score < best[0]:
                best = (score, rows, columns)
    return (best[1], best[2]) if best else (2, 2)


def crop_is_empty(image: Image.Image, box: tuple[int, int, int, int]) -> bool:
    crop = image.crop(box).convert("RGB")
    extrema = ImageChops.invert(crop).getbbox()
    return extrema is None or crop.getbbox() is None


def resize_image(image: Image.Image, size_text: str, mode: str) -> Image.Image:
    if size_text == "Original":
        return image.copy()
    width, height = parse_size(size_text)
    if mode == "Stretch to exact size":
        return image.resize((width, height), Image.Resampling.LANCZOS)
    if mode == "Fit inside and pad":
        return ImageOps.pad(image, (width, height), method=Image.Resampling.LANCZOS, color=(0, 0, 0))
    if mode == "Center crop":
        return ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    output = image.copy()
    output.thumbnail((width, height), Image.Resampling.LANCZOS)
    return output


def parse_size(size_text: str) -> tuple[int, int]:
    text = size_text.strip().lower().replace(" ", "")
    if "x" not in text:
        value = int(text)
        return value, value
    left, right = text.split("x", 1)
    return int(left), int(right)


def load_settings() -> dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def clean_folder_preferences(raw: dict[str, Any] | None = None) -> dict[str, str]:
    prefs = dict(DEFAULT_FOLDER_PREFERENCES)
    if isinstance(raw, dict):
        for key, default in DEFAULT_FOLDER_PREFERENCES.items():
            value = str(raw.get(key, default)).strip().replace("\\", "/").strip("/")
            parts = [part for part in value.split("/") if part]
            if value and not Path(value).is_absolute() and ".." not in parts:
                prefs[key] = "/".join(parts)
    return prefs


@dataclass
class ImageRecord:
    filename: str
    bucket: str = "Needs Review"
    caption: str = ""
    source_image: str = ""
    crop_box: list[int] = field(default_factory=list)
    notes: str = ""
    reason_tags: list[str] = field(default_factory=list)


class Manifest:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "manifest.json"
        self.data: dict[str, Any] = self.default()
        self.load()

    def default(self) -> dict[str, Any]:
        return {
            "manifest_version": 1,
            "app_version": APP_VERSION,
            "dataset": {"name": self.root.name, "root": str(self.root), "created": timestamp(), "last_exported": ""},
            "trigger": "",
            "caption_mode": "Manual / Template only",
            "training_target_profile": "Unknown/custom",
            "export": {"size": "1024x1024", "resize_mode": "Keep aspect ratio", "folder": str(self.root / DEFAULT_FOLDER_PREFERENCES["export"])},
            "images": [],
            "history": [],
            "ostris_configs": [],
        }

    def load(self) -> None:
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                self.data = {**self.default(), **loaded}
            except Exception:
                backup = self.path.with_suffix(f".broken_{timestamp()}.json")
                shutil.copy2(self.path, backup)
        else:
            self.save("manifest created")

    def save(self, action: str = "") -> None:
        self.data["app_version"] = APP_VERSION
        self.data["dataset"]["root"] = str(self.root)
        if action:
            self.data.setdefault("history", []).append({"time": timestamp(), "action": action})
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def record_for(self, filename: str) -> dict[str, Any]:
        for record in self.data.setdefault("images", []):
            if record.get("filename") == filename:
                return record
        record = ImageRecord(filename=filename).__dict__
        self.data["images"].append(record)
        return record


class EmptyManifest:
    def __init__(self) -> None:
        self.root = DEFAULT_DATASETS_DIR
        self.path = DEFAULT_DATASETS_DIR / "manifest.json"
        self.data = {
            "manifest_version": 1,
            "app_version": APP_VERSION,
            "dataset": {"name": "", "root": "", "created": "", "last_exported": ""},
            "trigger": "",
            "caption_mode": "Manual / Template only",
            "training_target_profile": "Unknown/custom",
            "export": {"size": "1024x1024", "resize_mode": "Keep aspect ratio", "folder": ""},
            "images": [],
            "history": [],
            "ostris_configs": [],
        }

    def save(self, action: str = "") -> None:
        return

    def record_for(self, filename: str) -> dict[str, Any]:
        return ImageRecord(filename=filename).__dict__


class CaptionWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(int, object, object, bool, str)

    def __init__(self, captioner, images: list[Path], trigger: str, mode: str, settings: dict[str, Any]) -> None:
        super().__init__()
        self.captioner = captioner
        self.images = images
        self.trigger = trigger
        self.mode = mode
        self.settings = settings
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        made = 0
        failed: list[str] = []
        records: list[tuple[str, str]] = []
        cancelled = False
        for index, image_path in enumerate(self.images, start=1):
            if self.cancel_requested:
                cancelled = True
                break
            try:
                caption = self.captioner(image_path, self.trigger, self.mode, self.settings)
                if not caption.strip():
                    raise RuntimeError("caption backend returned empty text")
                image_path.with_suffix(CAPTION_EXT).write_text(caption, encoding="utf-8")
                records.append((image_path.name, caption))
                made += 1
            except Exception as exc:
                failed.append(f"{image_path.name}: {exc}")
            self.progress.emit(index, f"Generating captions: {image_path.name}")
        self.finished.emit(made, failed, records, cancelled, self.mode)


class SplitExportWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object, object, bool, int, object, str)

    def __init__(
        self,
        inputs: list[Path],
        mode: str,
        output_text: str,
        split_folder_name: str,
        auto_detect: bool,
        rows: int,
        cols: int,
        crop: int,
        face_crops: dict[str, list[tuple[int, int, int, int]]],
        manual_crops: dict[str, list[tuple[int, int, int, int]]],
        naming_pattern: str,
        final_export_dir: Path | None,
        resize_final: bool,
        resize_target: str,
        resize_mode: str,
    ) -> None:
        super().__init__()
        self.inputs = inputs
        self.mode = mode
        self.output_text = output_text
        self.split_folder_name = split_folder_name
        self.auto_detect = auto_detect
        self.rows = rows
        self.cols = cols
        self.crop = crop
        self.face_crops = face_crops
        self.manual_crops = manual_crops
        self.naming_pattern = naming_pattern
        self.final_export_dir = final_export_dir
        self.resize_final = resize_final
        self.resize_target = resize_target
        self.resize_mode = resize_mode
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        created: list[Path] = []
        log: list[str] = []
        cancelled = False
        copied = 0
        copy_failed: list[str] = []
        for source_step, path in enumerate(self.inputs, start=1):
            if self.cancel_requested:
                cancelled = True
                log.append("STOPPED: export cancelled before next source image.")
                break
            out_dir = Path(self.output_text) if self.output_text else path.parent / self.split_folder_name
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                with Image.open(path) as image:
                    if self.mode == "Grid / Sheet":
                        rows, cols = detect_grid(image.width, image.height) if self.auto_detect else (self.rows, self.cols)
                        boxes = grid_boxes(image.width, image.height, rows, cols, self.crop)
                        mode_name = "grid"
                    elif self.mode == "Face crops":
                        boxes = self.face_crops.get(normalized_path_key(path), [])
                        rows, cols = 1, max(1, len(boxes))
                        mode_name = "face"
                    else:
                        boxes = self.manual_crops.get(normalized_path_key(path), [])
                        rows, cols = 1, max(1, len(boxes))
                        mode_name = "manual"
                    if not boxes:
                        log.append(f"SKIP {path.name}: no {mode_name} crop boxes")
                    for index, box in enumerate(boxes, start=1):
                        if self.cancel_requested:
                            cancelled = True
                            log.append(f"STOPPED {path.name}: export cancelled after {index - 1} crop(s).")
                            break
                        if box[2] <= box[0] or box[3] <= box[1]:
                            log.append(f"FAILED {path.name} #{index}: empty geometry {box}")
                            continue
                        if crop_is_empty(image, box):
                            log.append(f"ODD {path.name} #{index}: crop may be empty")
                        row = ((index - 1) // cols) + 1
                        col = ((index - 1) % cols) + 1
                        name = self.naming_pattern.format(source_name=path.stem, row=f"{row:02d}", col=f"{col:02d}", index=f"{index:02d}", mode=mode_name)
                        output = unique_path(out_dir / name)
                        cell = image.crop(box)
                        cell.save(output)
                        created.append(output)
                    if boxes:
                        log.append(f"OK {path.name}: {len(boxes)} {mode_name} cut(s) to {out_dir}")
            except Exception as exc:
                log.append(f"FAILED {path.name}: {exc}")
            self.progress.emit(source_step, f"Exporting cuts: {path.name}")
            if cancelled:
                break
        if created and self.final_export_dir is not None and not cancelled:
            self.final_export_dir.mkdir(parents=True, exist_ok=True)
            for index, image_path in enumerate(created, start=1):
                if self.cancel_requested:
                    cancelled = True
                    break
                try:
                    out_path = unique_path(self.final_export_dir / image_path.name)
                    with Image.open(image_path) as image:
                        output = resize_image(image.convert("RGB"), self.resize_target, self.resize_mode) if self.resize_final else image.convert("RGB")
                        output.save(out_path)
                    copied += 1
                except Exception as exc:
                    copy_failed.append(f"{image_path.name}: {exc}")
                self.progress.emit(len(self.inputs), f"Copying cuts to final export: {image_path.name}")
            log.append(f"FINAL EXPORT {self.final_export_dir}: copied {copied} file(s), skipped {len(copy_failed)}")
        self.finished.emit(created, log, cancelled, copied, copy_failed, str(self.final_export_dir or ""))


class AccentSelectionDelegate(QStyledItemDelegate):
    def __init__(self, color_provider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color_provider = color_provider

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        selected = bool(option.state & QStyle.State_Selected)
        clean_option = QStyleOptionViewItem(option)
        if selected:
            clean_option.state &= ~QStyle.State_Selected
        super().paint(painter, clean_option, index)
        if not selected:
            return
        color = QColor(self.color_provider())
        if not color.isValid():
            color = QColor(THEME["accent"])
        painter.save()
        tint = QColor(color)
        tint.setAlpha(72)
        border = QColor(color)
        border.setAlpha(210)
        rect = option.rect.adjusted(2, 2, -2, -2)
        if option.widget is not None and option.widget.property("selection_tint_icon_rect"):
            icon_option = QStyleOptionViewItem(option)
            self.initStyleOption(icon_option, index)
            icon_rect = option.widget.style().subElementRect(QStyle.SE_ItemViewItemDecoration, icon_option, option.widget)
            if icon_rect.isValid() and not icon_rect.isEmpty():
                rect = icon_rect.adjusted(-2, -2, 2, 2)
        painter.fillRect(rect, tint)
        painter.setPen(QPen(border, 2))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        painter.restore()


class DropListWidget(QListWidget):
    files_dropped = Signal(list)
    empty_clicked = Signal()

    def __init__(self, empty_text: str, icon_size: int = 86) -> None:
        super().__init__()
        self.empty_text = empty_text
        self.accent_color = THEME["accent"]
        self.setItemDelegate(AccentSelectionDelegate(lambda: self.accent_color, self))
        self.setAcceptDrops(True)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setResizeMode(QListWidget.Adjust)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setMinimumHeight(180)
        self.show_empty()

    def set_accent_color(self, color: str) -> None:
        self.accent_color = color
        self.viewport().update()

    def show_empty(self) -> None:
        self.clear()
        item = QListWidgetItem(self.empty_text)
        item.setFlags(Qt.NoItemFlags)
        self.addItem(item)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        files = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.files_dropped.emit(files)
        event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if self.count() == 1 and not self.item(0).data(Qt.UserRole):
            self.empty_clicked.emit()
            return
        super().mousePressEvent(event)


class ProjectDropWidget(QWidget):
    project_dropped = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        folders = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        for folder in folders:
            if folder.is_dir():
                self.project_dropped.emit(folder)
                break
        event.acceptProposedAction()


class ClickCloseLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        event.accept()


class ClickCloseScrollArea(QScrollArea):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        event.accept()


class ImagePreview(QLabel):
    crop_drawn = Signal(tuple)
    crop_changed = Signal(tuple)
    crop_removed = Signal()
    boxes_changed = Signal(list)

    def __init__(self, empty_text: str = "Preview appears here.") -> None:
        super().__init__(empty_text)
        self.empty_text = empty_text
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(440, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.source_pixmap = QPixmap()
        self.rows = 1
        self.columns = 1
        self.crop = (0, 0, 0, 0)
        self.draw_grid = False
        self.boxes: list[tuple[int, int, int, int]] = []
        self.drawing_enabled = False
        self.box_editing_enabled = False
        self.drag_start: QPoint | None = None
        self.drag_current: QPoint | None = None
        self.moving_box = False
        self.active_box_index: int | None = None
        self.move_box_start: tuple[int, int, int, int] | None = None
        self.move_image_start: tuple[int, int] | None = None
        self.resizing_box = False
        self.resize_anchor: tuple[int, int] | None = None
        self.aspect_ratio: float | None = None
        self.accent_color = THEME["accent"]

    def set_accent_color(self, color: str) -> None:
        self.accent_color = color
        self.update_preview()

    def set_image(self, path: Path | None) -> None:
        self.source_pixmap = QPixmap()
        self.drag_start = None
        self.drag_current = None
        if not path or not path.exists():
            self.setPixmap(QPixmap())
            self.setText(self.empty_text)
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.setText(f"Could not preview:\n{path.name}")
            return
        self.source_pixmap = pixmap
        self.setText("")
        self.update_preview()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.source_pixmap.isNull():
            self.update_preview()

    def set_grid(self, rows: int, columns: int, crop: tuple[int, int, int, int]) -> None:
        self.rows = max(1, rows)
        self.columns = max(1, columns)
        self.crop = crop
        self.draw_grid = True
        self.update_preview()

    def set_boxes(self, boxes: list[tuple[int, int, int, int]], draw_grid: bool = False) -> None:
        self.boxes = boxes
        self.draw_grid = draw_grid
        self.update_preview()

    def set_crop_drawing_enabled(self, enabled: bool) -> None:
        self.drawing_enabled = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)
        self.reset_box_interaction()
        self.update_preview()

    def set_box_editing_enabled(self, enabled: bool) -> None:
        self.box_editing_enabled = enabled
        if not self.drawing_enabled:
            self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)
        self.reset_box_interaction()
        self.update_preview()

    def reset_box_interaction(self) -> None:
        self.drag_start = None
        self.drag_current = None
        self.moving_box = False
        self.active_box_index = None
        self.move_box_start = None
        self.move_image_start = None
        self.resizing_box = False
        self.resize_anchor = None

    def set_crop_aspect_ratio(self, ratio: float | None) -> None:
        self.aspect_ratio = ratio

    def box_at_point(self, point: QPoint) -> tuple[int, tuple[int, int, int, int]] | None:
        image_point = self.point_to_image(point)
        if image_point is None:
            return None
        x, y = image_point
        for index, box in reversed(list(enumerate(self.boxes))):
            left, top, right, bottom = box
            if left <= x <= right and top <= y <= bottom:
                return index, box
        return None

    def corner_at_point(self, point: QPoint) -> tuple[str, int, tuple[int, int, int, int]] | None:
        if not self.boxes:
            return None
        handle_size = 9
        for index, box in reversed(list(enumerate(self.boxes))):
            rect = self.image_box_to_preview(box)
            corners = {
                "top_left": rect.topLeft(),
                "top_right": rect.topRight(),
                "bottom_left": rect.bottomLeft(),
                "bottom_right": rect.bottomRight(),
            }
            for name, corner in corners.items():
                hit = QRect(corner.x() - handle_size, corner.y() - handle_size, handle_size * 2, handle_size * 2)
                if hit.contains(point):
                    return name, index, box
        return None

    def resize_anchor_for_corner(self, corner: str, box: tuple[int, int, int, int]) -> tuple[int, int]:
        left, top, right, bottom = box
        anchors = {
            "top_left": (right, bottom),
            "top_right": (left, bottom),
            "bottom_left": (right, top),
            "bottom_right": (left, top),
        }
        return anchors[corner]

    def aspect_box(self, start: tuple[int, int], end: tuple[int, int]) -> tuple[int, int, int, int]:
        sx, sy = start
        ex, ey = end
        if not self.aspect_ratio:
            left, right = sorted([sx, ex])
            top, bottom = sorted([sy, ey])
            return (left, top, right, bottom)
        dx = ex - sx
        dy = ey - sy
        sign_x = 1 if dx >= 0 else -1
        sign_y = 1 if dy >= 0 else -1
        raw_width = abs(dx)
        raw_height = abs(dy)
        if raw_width <= 0 and raw_height <= 0:
            return (sx, sy, sx, sy)
        max_width = self.source_pixmap.width() - sx if sign_x >= 0 else sx
        max_height = self.source_pixmap.height() - sy if sign_y >= 0 else sy
        if raw_width / max(1, raw_height) > self.aspect_ratio:
            width = raw_width
            height = round(width / self.aspect_ratio)
        else:
            height = raw_height
            width = round(height * self.aspect_ratio)
        if width > max_width:
            width = max_width
            height = round(width / self.aspect_ratio)
        if height > max_height:
            height = max_height
            width = round(height * self.aspect_ratio)
        width = max(1, width)
        height = max(1, height)
        left = sx if sign_x >= 0 else sx - width
        right = sx + width if sign_x >= 0 else sx
        top = sy if sign_y >= 0 else sy - height
        bottom = sy + height if sign_y >= 0 else sy
        return (round(left), round(top), round(right), round(bottom))

    def clamp_image_box(self, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        if self.source_pixmap.isNull():
            return box
        left, top, right, bottom = box
        width = max(1, right - left)
        height = max(1, bottom - top)
        if left < 0:
            right -= left
            left = 0
        if top < 0:
            bottom -= top
            top = 0
        if right > self.source_pixmap.width():
            left -= right - self.source_pixmap.width()
            right = self.source_pixmap.width()
        if bottom > self.source_pixmap.height():
            top -= bottom - self.source_pixmap.height()
            bottom = self.source_pixmap.height()
        left = max(0, left)
        top = max(0, top)
        right = min(self.source_pixmap.width(), max(left + width, right))
        bottom = min(self.source_pixmap.height(), max(top + height, bottom))
        return (round(left), round(top), round(right), round(bottom))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_preview()

    def scaled_preview_size(self) -> QSize:
        if self.source_pixmap.isNull():
            return QSize()
        return self.source_pixmap.scaled(self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation).size()

    def preview_rect(self) -> QRect:
        size = self.scaled_preview_size()
        rect = self.contentsRect()
        left = rect.left() + (rect.width() - size.width()) // 2
        top = rect.top() + (rect.height() - size.height()) // 2
        return QRect(left, top, size.width(), size.height())

    def point_to_image(self, point: QPoint, clamp: bool = False) -> tuple[int, int] | None:
        if self.source_pixmap.isNull():
            return None
        rect = self.preview_rect()
        if not rect.contains(point) and not clamp:
            return None
        px = min(max(point.x(), rect.left()), rect.left() + rect.width()) if clamp else point.x()
        py = min(max(point.y(), rect.top()), rect.top() + rect.height()) if clamp else point.y()
        x = round((px - rect.left()) * self.source_pixmap.width() / max(1, rect.width()))
        y = round((py - rect.top()) * self.source_pixmap.height() / max(1, rect.height()))
        return (min(max(0, x), self.source_pixmap.width()), min(max(0, y), self.source_pixmap.height()))

    def image_box_to_preview(self, box: tuple[int, int, int, int]) -> QRect:
        rect = self.preview_rect()
        left, top, right, bottom = box
        x = rect.left() + round(left * rect.width() / max(1, self.source_pixmap.width()))
        y = rect.top() + round(top * rect.height() / max(1, self.source_pixmap.height()))
        w = round((right - left) * rect.width() / max(1, self.source_pixmap.width()))
        h = round((bottom - top) * rect.height() / max(1, self.source_pixmap.height()))
        return QRect(x, y, w, h)

    def mousePressEvent(self, event) -> None:
        if self.drawing_enabled or self.box_editing_enabled:
            point = event.position().toPoint()
            corner = self.corner_at_point(point)
            hit = self.box_at_point(point)
            if event.button() == Qt.RightButton and hit:
                del self.boxes[hit[0]]
                self.boxes_changed.emit(list(self.boxes))
                if self.drawing_enabled or self.box_editing_enabled:
                    self.crop_removed.emit()
                self.update_preview()
                return
            if event.button() == Qt.LeftButton and corner:
                self.resizing_box = True
                self.resize_anchor = self.resize_anchor_for_corner(corner[0], corner[2])
                self.active_box_index = corner[1]
                self.setCursor(Qt.SizeFDiagCursor if corner[0] in {"top_left", "bottom_right"} else Qt.SizeBDiagCursor)
                return
            if event.button() == Qt.LeftButton and hit:
                image_point = self.point_to_image(point)
                if image_point:
                    self.moving_box = True
                    self.active_box_index = hit[0]
                    self.move_box_start = hit[1]
                    self.move_image_start = image_point
                    self.setCursor(Qt.ClosedHandCursor)
                    return
            if event.button() == Qt.LeftButton and self.boxes:
                return
            if self.drawing_enabled and event.button() == Qt.LeftButton and self.point_to_image(point):
                self.drag_start = point
                self.drag_current = self.drag_start
                self.update_preview()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (self.drawing_enabled or self.box_editing_enabled) and self.resizing_box and self.resize_anchor:
            current = self.point_to_image(event.position().toPoint(), clamp=True)
            if current:
                resized = self.aspect_box(self.resize_anchor, current)
                if resized[2] - resized[0] >= 8 and resized[3] - resized[1] >= 8:
                    index = self.active_box_index if self.active_box_index is not None else 0
                    if 0 <= index < len(self.boxes):
                        self.boxes[index] = resized
                    self.update_preview()
            return
        if (self.drawing_enabled or self.box_editing_enabled) and self.moving_box and self.move_box_start and self.move_image_start:
            current = self.point_to_image(event.position().toPoint(), clamp=True)
            if current:
                dx = current[0] - self.move_image_start[0]
                dy = current[1] - self.move_image_start[1]
                left, top, right, bottom = self.move_box_start
                moved = self.clamp_image_box((left + dx, top + dy, right + dx, bottom + dy))
                index = self.active_box_index if self.active_box_index is not None else 0
                if 0 <= index < len(self.boxes):
                    self.boxes[index] = moved
                self.update_preview()
            return
        if self.drawing_enabled and self.drag_start is not None:
            self.drag_current = event.position().toPoint()
            self.update_preview()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if (self.drawing_enabled or self.box_editing_enabled) and self.resizing_box and event.button() == Qt.LeftButton:
            self.resizing_box = False
            self.resize_anchor = None
            self.setCursor(Qt.CrossCursor)
            if self.boxes:
                index = self.active_box_index if self.active_box_index is not None else 0
                if 0 <= index < len(self.boxes):
                    self.crop_changed.emit(self.boxes[index])
                self.boxes_changed.emit(list(self.boxes))
            self.active_box_index = None
            return
        if (self.drawing_enabled or self.box_editing_enabled) and self.moving_box and event.button() == Qt.LeftButton:
            self.moving_box = False
            self.active_box_index = None
            self.move_box_start = None
            self.move_image_start = None
            self.resizing_box = False
            self.resize_anchor = None
            self.setCursor(Qt.CrossCursor)
            if self.boxes:
                self.crop_changed.emit(self.boxes[0])
                self.boxes_changed.emit(list(self.boxes))
            return
        if self.drawing_enabled and self.drag_start is not None and event.button() == Qt.LeftButton:
            start = self.point_to_image(self.drag_start)
            end = self.point_to_image(event.position().toPoint(), clamp=True)
            self.drag_start = None
            self.drag_current = None
            if start and end:
                left, top, right, bottom = self.aspect_box(start, end)
                if right - left >= 8 and bottom - top >= 8:
                    self.crop_drawn.emit((left, top, right, bottom))
            self.update_preview()
            return
        super().mouseReleaseEvent(event)

    def update_preview(self) -> None:
        if self.source_pixmap.isNull():
            return
        scaled = self.source_pixmap.scaled(self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painted = QPixmap(scaled)
        painter = QPainter(painted)
        if self.draw_grid:
            pen = QPen(QColor(self.accent_color))
            pen.setWidth(3)
            painter.setPen(pen)
            w_scale = painted.width() / max(1, self.source_pixmap.width())
            h_scale = painted.height() / max(1, self.source_pixmap.height())
            boxes = grid_boxes(self.source_pixmap.width(), self.source_pixmap.height(), self.rows, self.columns, self.crop)
            for box in boxes:
                left, top, right, bottom = box
                painter.drawRect(round(left * w_scale), round(top * h_scale), round((right - left) * w_scale), round((bottom - top) * h_scale))
        if self.boxes:
            fill = QColor(self.accent_color)
            fill.setAlpha(42)
            pen = QPen(QColor(self.accent_color))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(fill)
            w_scale = painted.width() / max(1, self.source_pixmap.width())
            h_scale = painted.height() / max(1, self.source_pixmap.height())
            for box in self.boxes:
                left, top, right, bottom = box
                rect = QRect(round(left * w_scale), round(top * h_scale), round((right - left) * w_scale), round((bottom - top) * h_scale))
                painter.drawRect(rect)
                if self.drawing_enabled:
                    handle_fill = QColor(self.accent_color)
                    handle_fill.setAlpha(235)
                    painter.setBrush(handle_fill)
                    painter.setPen(QPen(QColor("#ffffff"), 2))
                    for corner in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                        painter.drawEllipse(corner, 5, 5)
        if self.drag_start is not None and self.drag_current is not None:
            start = self.point_to_image(self.drag_start)
            end = self.point_to_image(self.drag_current, clamp=True)
            scaled_rect = QRect()
            if start and end:
                left, top, right, bottom = self.aspect_box(start, end)
                w_scale = painted.width() / max(1, self.source_pixmap.width())
                h_scale = painted.height() / max(1, self.source_pixmap.height())
                scaled_rect = QRect(round(left * w_scale), round(top * h_scale), round((right - left) * w_scale), round((bottom - top) * h_scale))
            fill = QColor(self.accent_color)
            fill.setAlpha(32)
            pen = QPen(QColor(self.accent_color))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(fill)
            if scaled_rect.isValid():
                painter.drawRect(scaled_rect)
        painter.end()
        self.setPixmap(painted)


def thumb_item(path: Path, label: str | None = None) -> QListWidgetItem:
    item = QListWidgetItem(label or path.name)
    item.setData(Qt.UserRole, str(path))
    icon = cached_thumbnail_icon(path, 96)
    if not icon.isNull():
        item.setIcon(icon)
    return item


def sheet_grid_item(path: Path) -> QListWidgetItem:
    item = QListWidgetItem("")
    item.setData(Qt.UserRole, str(path))
    item.setToolTip(path.name)
    item.setTextAlignment(Qt.AlignCenter)
    item.setSizeHint(QSize(SPLIT_THUMB_TILE, SPLIT_THUMB_TILE))
    icon = cached_thumbnail_icon(path, SPLIT_THUMB_ICON)
    if not icon.isNull():
        item.setIcon(icon)
    return item


def library_thumb_item(path: Path) -> QListWidgetItem:
    item = QListWidgetItem("")
    item.setData(Qt.UserRole, str(path))
    item.setToolTip(path.name)
    item.setTextAlignment(Qt.AlignCenter)
    item.setSizeHint(QSize(138, 138))
    icon = cached_thumbnail_icon(path, 160)
    if not icon.isNull():
        item.setIcon(icon)
    return item


def add_help(widget: QWidget, text: str) -> QWidget:
    widget.setToolTip(text)
    return widget


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num_bytes} B"


def local_path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except Exception:
            continue
    return total


def local_model_size_text(target_folder: str) -> str:
    if not target_folder.strip():
        return "Not downloaded"
    size = local_path_size(Path(target_folder))
    return human_size(size) if size > 0 else "Not downloaded"


def model_target_downloaded(target_folder: str) -> bool:
    if not target_folder.strip():
        return False
    path = Path(target_folder)
    if not path.exists():
        return False
    if path.is_file():
        return path.stat().st_size > 0
    try:
        return any(child.is_file() for child in path.rglob("*"))
    except Exception:
        return False


def path_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def model_target_can_be_removed(target_folder: str, settings: dict[str, Any]) -> tuple[bool, str]:
    if not target_folder.strip():
        return False, "No target folder is configured."
    target = Path(target_folder).resolve()
    if not target.exists():
        return False, "The target folder does not exist."
    roots = [DEFAULT_MODELS_DIR.resolve()]
    roots.extend(Path(path).resolve() for path in settings.get("caption_model_locations", []))
    matching_roots = [root for root in roots if path_inside(target, root)]
    if not matching_roots:
        return False, "For safety, the app only removes model files inside the app models folder or configured caption model locations."
    if any(target == root for root in matching_roots):
        return False, "Refusing to remove an entire configured model root. Select a model sub-folder instead."
    return True, ""


class ModelRegistryDialog(QDialog):
    def __init__(self, settings: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.registry = [dict(item) for item in settings.get("caption_model_registry", default_caption_model_registry())]
        self.download_process: QProcess | None = None
        self.download_output = ""
        self.setWindowTitle("Caption Model Registry")
        self.resize(1380, 860)
        self.setMinimumSize(1240, 780)
        layout = QVBoxLayout(self)
        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.model_list = QListWidget()
        self.model_list.setMinimumWidth(500)
        self.model_list.currentRowChanged.connect(self.load_entry)
        left_layout.addWidget(self.model_list, 1)
        left_actions = QHBoxLayout()
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove")
        reset_btn = QPushButton("Reset Built-ins")
        refresh_all_sizes = QPushButton("Refresh Local Sizes")
        add_btn.clicked.connect(self.add_entry)
        remove_btn.clicked.connect(self.remove_entry)
        reset_btn.clicked.connect(self.reset_builtins)
        refresh_all_sizes.clicked.connect(self.refresh_all_local_sizes)
        left_actions.addWidget(add_help(add_btn, "Add a custom model preset."))
        left_actions.addWidget(add_help(remove_btn, "Remove the selected preset from local settings."))
        left_actions.addWidget(add_help(reset_btn, "Replace registry with current built-in starter presets."))
        left_actions.addWidget(add_help(refresh_all_sizes, "Refresh local disk-size status for all registry entries."))
        left_layout.addLayout(left_actions)
        split.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.name = QLineEdit()
        self.backend = QComboBox()
        self.backend.addItems(["JoyCaption", "Qwen3-VL 8B", "Qwen3-VL 4B", "Qwen3-VL 2B", "Florence-2", "BLIP", "WD14 tagger", "Custom command"])
        self.provider = QComboBox()
        self.provider.addItems(["Hugging Face", "Civitai", "GitHub", "Direct URL", "Local folder", "Other"])
        self.repo = QLineEdit()
        self.url = QLineEdit()
        self.size = QLineEdit()
        self.size.setReadOnly(True)
        self.target_folder = QLineEdit()
        self.target_folder.editingFinished.connect(self.update_download_state)
        browse_target = QPushButton("Browse")
        browse_target.clicked.connect(self.browse_target_folder)
        target_row = QHBoxLayout()
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.addWidget(self.target_folder, 1)
        target_row.addWidget(browse_target)
        self.target_row = QWidget()
        self.target_row.setLayout(target_row)
        self.download_command = QPlainTextEdit()
        self.download_command.setMinimumHeight(72)
        self.download_command.textChanged.connect(self.update_download_state)
        self.notes = QPlainTextEdit()
        self.notes.setMinimumHeight(92)
        form.addRow("Name", add_help(self.name, "User-facing preset name."))
        form.addRow("Backend", add_help(self.backend, "Caption backend this preset is meant to run with."))
        form.addRow("Provider", add_help(self.provider, "Where the model/download information comes from."))
        form.addRow("Repo / model id", add_help(self.repo, "Provider repo ID, model ID, or package name."))
        form.addRow("Source URL", add_help(self.url, "Model card, Civitai page, GitHub repo, or direct download page."))
        form.addRow("Local disk size", add_help(self.size, "Actual size currently found on local disk in the target folder."))
        form.addRow("Target folder", add_help(self.target_row, "Suggested local folder for this model."))
        form.addRow("Download command", add_help(self.download_command, "Editable command suggestion. The app does not run it automatically."))
        form.addRow("Notes / warnings", add_help(self.notes, "Size, license, dependency, privacy, or setup notes."))
        right_layout.addLayout(form)
        actions = QHBoxLayout()
        save_entry = QPushButton("Save Entry")
        use_entry = QPushButton("Use Selected")
        self.download_btn = QPushButton("Download Model")
        refresh_size = QPushButton("Refresh Local Size")
        self.remove_local_btn = QPushButton("Remove Local Files")
        open_page = QPushButton("Open Source Page")
        save_entry.clicked.connect(self.save_current_entry)
        use_entry.clicked.connect(self.use_selected_entry)
        self.download_btn.clicked.connect(self.download_selected_model)
        refresh_size.clicked.connect(self.refresh_selected_size)
        self.remove_local_btn.clicked.connect(self.remove_local_model_files)
        open_page.clicked.connect(self.open_source_page)
        actions.addWidget(add_help(save_entry, "Save edits to the selected registry entry."))
        actions.addWidget(add_help(use_entry, "Use this preset as the current local caption model selection."))
        actions.addWidget(add_help(self.download_btn, "Run the editable download command. Disabled when the target folder already contains model files."))
        actions.addWidget(add_help(refresh_size, "Recalculate the selected model's local disk size."))
        actions.addWidget(add_help(self.remove_local_btn, "Remove the selected model files from local disk after confirmation."))
        actions.addWidget(add_help(open_page, "Open the model source page in your browser."))
        actions.addStretch(1)
        right_layout.addLayout(actions)
        self.download_status = QLabel("Download idle.")
        self.download_status.setWordWrap(True)
        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setVisible(False)
        right_layout.addWidget(self.download_status)
        right_layout.addWidget(self.download_progress)
        split.addWidget(right)
        split.setSizes([540, 840])

        bottom = QHBoxLayout()
        save = QPushButton("Save Registry")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        bottom.addStretch(1)
        bottom.addWidget(save)
        bottom.addWidget(cancel)
        layout.addLayout(bottom)
        self.refresh_list()

    def refresh_list(self) -> None:
        current = max(0, self.model_list.currentRow())
        self.model_list.clear()
        for entry in self.registry:
            size = local_model_size_text(entry.get("target_folder", ""))
            downloaded = model_target_downloaded(entry.get("target_folder", ""))
            state = "downloaded" if downloaded else "not downloaded"
            item = QListWidgetItem(f"{entry.get('name', 'Untitled')}  [{entry.get('provider', '')}]  {size}  {state}")
            item.setForeground(QColor("#6dff8f" if downloaded else "#ff6d6d"))
            self.model_list.addItem(item)
        if self.registry:
            self.model_list.setCurrentRow(min(current, len(self.registry) - 1))

    def entry_from_fields(self) -> dict[str, str]:
        return {
            "name": self.name.text().strip(),
            "backend": self.backend.currentText(),
            "provider": self.provider.currentText(),
            "repo": self.repo.text().strip(),
            "url": self.url.text().strip(),
            "size": self.size.text().strip(),
            "target_folder": self.target_folder.text().strip(),
            "download_command": self.download_command.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
        }

    def load_entry(self, row: int) -> None:
        if row < 0 or row >= len(self.registry):
            return
        entry = self.registry[row]
        self.name.setText(entry.get("name", ""))
        self.backend.setCurrentText(entry.get("backend", "Custom command"))
        self.provider.setCurrentText(entry.get("provider", "Other"))
        self.repo.setText(entry.get("repo", ""))
        self.url.setText(entry.get("url", ""))
        self.target_folder.setText(entry.get("target_folder", str(DEFAULT_MODELS_DIR)))
        self.size.setText(local_model_size_text(self.target_folder.text()))
        self.download_command.setPlainText(entry.get("download_command", ""))
        self.notes.setPlainText(entry.get("notes", ""))
        self.update_download_state()

    def save_current_entry(self) -> None:
        row = self.model_list.currentRow()
        if row < 0:
            return
        self.registry[row] = self.entry_from_fields()
        self.refresh_list()
        self.update_download_state()

    def add_entry(self) -> None:
        self.registry.append(
            {
                "name": "Custom Caption Model",
                "backend": "Custom command",
                "provider": "Other",
                "repo": "",
                "url": "",
                "size": "Unknown",
                "target_folder": str(DEFAULT_MODELS_DIR / "custom-caption-model"),
                "download_command": "",
                "notes": "",
            }
        )
        self.refresh_list()
        self.model_list.setCurrentRow(len(self.registry) - 1)

    def remove_entry(self) -> None:
        row = self.model_list.currentRow()
        if 0 <= row < len(self.registry):
            del self.registry[row]
            self.refresh_list()

    def reset_builtins(self) -> None:
        self.registry = default_caption_model_registry()
        self.refresh_list()

    def update_download_state(self) -> None:
        if not hasattr(self, "download_btn"):
            return
        if self.download_process is not None:
            self.download_btn.setEnabled(False)
            if hasattr(self, "remove_local_btn"):
                self.remove_local_btn.setEnabled(False)
            self.download_btn.setText("Downloading...")
            self.download_btn.setToolTip("A model download is already running.")
            return
        downloaded = model_target_downloaded(self.target_folder.text().strip())
        has_command = bool(self.download_command.toPlainText().strip())
        self.size.setText(local_model_size_text(self.target_folder.text()))
        self.download_btn.setEnabled(has_command and not downloaded)
        self.download_btn.setText("Already Downloaded" if downloaded else "Download Model")
        self.download_btn.setToolTip(
            "This target folder already contains files, so the app will not download the same model again."
            if downloaded
            else "Run the editable download command in a terminal window."
        )
        if hasattr(self, "remove_local_btn"):
            self.remove_local_btn.setEnabled(downloaded)
            self.remove_local_btn.setToolTip("Remove local model files from disk." if downloaded else "No local model files found at this target path.")

    def download_selected_model(self) -> None:
        entry = self.entry_from_fields()
        target = entry.get("target_folder", "")
        if model_target_downloaded(target):
            QMessageBox.information(self, APP_NAME, f"Model already appears to be downloaded:\n\n{target}")
            self.update_download_state()
            return
        command = entry.get("download_command", "").strip()
        if not command:
            QMessageBox.information(self, APP_NAME, "This registry entry has no download command.")
            return
        reply = QMessageBox.question(
            self,
            "Download Model",
            f"Run this download command?\n\n{command}\n\nTarget:\n{target}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            process = QProcess(self)
            process.setWorkingDirectory(str(APP_DIR))
            process.setProcessChannelMode(QProcess.MergedChannels)
            process.readyReadStandardOutput.connect(self.capture_download_output)
            process.readyReadStandardError.connect(self.capture_download_output)
            process.finished.connect(self.download_finished)
            self.download_process = process
            self.download_output = ""
            self.download_progress.setRange(0, 0)
            self.download_progress.setVisible(True)
            self.download_status.setText(f"Downloading {entry.get('name', 'model')}...")
            self.update_download_state()
            if sys.platform == "win32":
                process.start("cmd.exe", ["/c", command])
            else:
                process.start("/bin/sh", ["-lc", command])
            if not process.waitForStarted(5000):
                raise RuntimeError("download command did not start")
        except Exception as exc:
            self.download_process = None
            self.download_progress.setVisible(False)
            self.update_download_state()
            QMessageBox.warning(self, APP_NAME, f"Could not start download command:\n\n{exc}")
            return
        self.save_current_entry()
        self.download_status.setText(f"Download running: {entry.get('name', 'model')}")

    def capture_download_output(self) -> None:
        if self.download_process is None:
            return
        text = bytes(self.download_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not text:
            text = bytes(self.download_process.readAllStandardError()).decode("utf-8", errors="replace")
        if text:
            self.download_output = (self.download_output + text)[-4000:]
            last_line = [line.strip() for line in self.download_output.replace("\r", "\n").splitlines() if line.strip()]
            if last_line:
                self.download_status.setText(last_line[-1][:240])

    def download_finished(self, exit_code: int, _exit_status) -> None:
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(100 if exit_code == 0 else 0)
        self.download_progress.setVisible(False)
        self.download_process = None
        self.refresh_list()
        self.update_download_state()
        if exit_code == 0:
            self.download_status.setText("Download finished. Registry refreshed.")
            QMessageBox.information(self, APP_NAME, "Model download finished.")
        else:
            self.download_status.setText(f"Download failed with exit code {exit_code}.")
            QMessageBox.warning(self, APP_NAME, f"Model download failed with exit code {exit_code}.\n\n{self.download_output[-1500:]}")

    def refresh_selected_size(self) -> None:
        row = self.model_list.currentRow()
        if row < 0 or row >= len(self.registry):
            return
        self.size.setText(local_model_size_text(self.target_folder.text()))
        self.registry[row] = self.entry_from_fields()
        self.refresh_list()
        self.update_download_state()

    def remove_local_model_files(self) -> None:
        target = self.target_folder.text().strip()
        allowed, reason = model_target_can_be_removed(target, self.settings)
        if not allowed:
            QMessageBox.warning(self, APP_NAME, reason)
            return
        path = Path(target).resolve()
        size_text = local_model_size_text(str(path))
        reply = QMessageBox.warning(
            self,
            "Remove Local Model Files",
            f"Remove this local model from disk?\n\n{path}\n\nCurrent size: {size_text}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        confirm, ok = QInputDialog.getText(self, "Confirm Remove", f"Type DELETE to remove:\n{path}")
        if not ok or confirm != "DELETE":
            return
        try:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not remove local model files:\n\n{exc}")
            return
        self.size.setText("Not downloaded")
        self.refresh_list()
        self.update_download_state()
        QMessageBox.information(self, APP_NAME, f"Removed local model files:\n\n{path}")

    def refresh_all_local_sizes(self) -> None:
        for index, entry in enumerate(self.registry):
            entry["size"] = local_model_size_text(entry.get("target_folder", ""))
            QApplication.processEvents()
        self.refresh_list()
        if self.registry:
            self.load_entry(max(0, self.model_list.currentRow()))
        QMessageBox.information(self, APP_NAME, "Local model sizes refreshed.")

    def browse_target_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose model target folder", self.target_folder.text() or str(DEFAULT_MODELS_DIR))
        if folder:
            self.target_folder.setText(folder)
            self.update_download_state()

    def open_source_page(self) -> None:
        url = self.url.text().strip()
        if url:
            os.startfile(url)

    def use_selected_entry(self) -> None:
        entry = self.entry_from_fields()
        self.settings["local_model_type"] = entry.get("backend", "")
        self.settings["model_path"] = entry.get("target_folder", "")
        self.settings["selected_caption_model_preset"] = entry.get("name", "")
        self.save_current_entry()

    def accept(self) -> None:
        self.save_current_entry()
        self.settings["caption_model_registry"] = self.registry
        super().accept()

class CaptionSettingsDialog(QDialog):
    def __init__(self, settings: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.controls_ready = False
        self.setWindowTitle("Caption Settings")
        self.resize(980, 760)
        self.setMinimumSize(900, 680)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        self.mode = QComboBox()
        self.mode.addItems(["Manual / Template only", "Local model", "Local server", "API model", "Custom command"])
        self.mode.setCurrentText(settings.get("caption_mode", "Manual / Template only"))
        self.profile = QComboBox()
        self.profile.addItems(["Z-Image Base/Turbo", "Flux-style LoRA", "SDXL character LoRA", "anime/tag models", "Unknown/custom"])
        self.profile.setCurrentText(settings.get("training_target_profile", "Unknown/custom"))
        self.local_model = QComboBox()
        model_locations = settings.get("caption_model_locations", [])
        default_model_path = settings.get("model_path") or (model_locations[0] if model_locations else str(DEFAULT_MODELS_DIR))
        self.model_path = QLineEdit(default_model_path)
        self.model_path.setReadOnly(True)
        self.browse_model = QPushButton("Registry")
        self.browse_model.clicked.connect(self.open_model_registry)
        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.addWidget(self.model_path, 1)
        model_row.addWidget(self.browse_model)
        self.model_path_row = QWidget()
        self.model_path_row.setLayout(model_row)
        self.device = QComboBox()
        self.device.addItems(["Auto", "CUDA", "CPU"])
        self.batch = QSpinBox()
        self.batch.setRange(1, 128)
        self.batch.setValue(int(settings.get("batch_size", 4)))
        self.api_provider = QComboBox()
        self.api_provider.addItems(["OpenAI", "Gemini", "Anthropic", "Custom HTTP"])
        self.api_provider.setCurrentText(settings.get("api_provider", "OpenAI"))
        self.api_model = QComboBox()
        self.api_model.setEditable(True)
        self.refresh_api_model_presets(settings.get("api_model", ""))
        self.local_server_provider = QComboBox()
        self.local_server_provider.addItems(["Ollama", "LM Studio", "KoboldCPP", "Custom OpenAI-compatible", "Custom JSON"])
        self.local_server_provider.setCurrentText(settings.get("local_server_provider", "Ollama"))
        self.local_server_url = QLineEdit(settings.get("local_server_url", self.default_local_server_url(self.local_server_provider.currentText())))
        self.local_server_model = QComboBox()
        self.local_server_model.setEditable(True)
        self.refresh_local_server_model_presets(settings.get("local_server_model", ""))
        self.refresh_server_models_btn = QPushButton("Refresh Models")
        self.refresh_server_models_btn.clicked.connect(self.refresh_local_server_models_from_host)
        self.command = QLineEdit(settings.get("caption_command", 'python caption.py --image "{image}" --trigger "{trigger}" --prompt "{prompt}"'))
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 3600)
        self.timeout.setValue(int(settings.get("caption_timeout", 120)))
        self.json_field = QLineEdit(settings.get("caption_json_field", "caption"))
        saved_template = settings.get("caption_template", DEFAULT_CAPTION_TEMPLATE)
        if saved_template == OLD_DEFAULT_CAPTION_TEMPLATE:
            saved_template = DEFAULT_CAPTION_TEMPLATE
        self.template = QPlainTextEdit(saved_template)
        self.template.setMinimumHeight(90)
        self.prompt_preset = QComboBox()
        self.prompt_preset.setEditable(False)
        self.caption_prompt = QPlainTextEdit(settings.get("caption_prompt", DEFAULT_CAPTION_PROMPT))
        self.caption_prompt.setMinimumHeight(120)
        self.load_prompt_presets()
        prompt_buttons = QHBoxLayout()
        self.load_prompt_btn = QPushButton("Load")
        self.save_prompt_btn = QPushButton("Save")
        self.remove_prompt_btn = QPushButton("Remove")
        self.default_prompt_btn = QPushButton("Built-in Default")
        self.load_prompt_btn.clicked.connect(self.load_selected_prompt_preset)
        self.save_prompt_btn.clicked.connect(self.save_current_prompt_preset)
        self.remove_prompt_btn.clicked.connect(self.remove_selected_prompt_preset)
        self.default_prompt_btn.clicked.connect(self.restore_default_prompt_preset)
        for button in [self.load_prompt_btn, self.save_prompt_btn, self.remove_prompt_btn, self.default_prompt_btn]:
            prompt_buttons.addWidget(button)
        self.prompt_button_row = QWidget()
        self.prompt_button_row.setLayout(prompt_buttons)
        self.profile_note = QLabel("")
        self.profile_note.setWordWrap(True)
        self.mode_note = QLabel("")
        self.mode_note.setWordWrap(True)
        self.registry_btn = QPushButton("Model Registry")
        self.registry_btn.clicked.connect(self.open_model_registry)
        form.addRow("Caption mode", add_help(self.mode, "Choose how captions are generated. Manual/template mode never sends images anywhere."))
        form.addRow("Active controls", self.mode_note)
        form.addRow("Training target profile", add_help(self.profile, "Editable recommendation profile; it suggests caption style and model defaults without locking them."))
        form.addRow("Local model", add_help(self.local_model, "Only downloaded models from the Caption Model Registry are selectable here."))
        form.addRow("Model path", add_help(self.model_path_row, "Read-only path for the selected downloaded local model."))
        form.addRow("Downloads", add_help(self.registry_btn, "Edit model download sources, repo IDs, target folders, and setup notes."))
        form.addRow("Device", add_help(self.device, "Auto lets the backend choose CUDA when available."))
        form.addRow("Batch size", add_help(self.batch, "How many images to caption per backend call."))
        form.addRow("API provider", add_help(self.api_provider, "Images are sent to the selected provider when API mode is used."))
        form.addRow("API model", add_help(self.api_model, "Vision-capable model name for API captioning."))
        form.addRow("Local server", add_help(self.local_server_provider, "Run captions through Ollama, LM Studio, KoboldCPP, or another local HTTP server."))
        form.addRow("Server URL", add_help(self.local_server_url, "Local caption endpoint. Ollama usually uses http://localhost:11434/api/generate. LM Studio usually uses http://localhost:1234/v1/chat/completions."))
        form.addRow("Server model", add_help(self.local_server_model, "Model name served by the local runtime. Refresh can pull visible models from Ollama or OpenAI-compatible /v1/models."))
        form.addRow("Server model list", add_help(self.refresh_server_models_btn, "Refresh available models from the selected local server if it exposes a model list endpoint."))
        form.addRow("Custom command", add_help(self.command, 'Use placeholders like "{image}" and "{trigger}".'))
        form.addRow("Timeout seconds", add_help(self.timeout, "Maximum runtime for one custom command call."))
        form.addRow("JSON field", add_help(self.json_field, "If command output is JSON, read this field for the caption."))
        form.addRow("Template", add_help(self.template, "Manual captions replace <trigger> and other known fields with editable text."))
        form.addRow("Prompt preset", add_help(self.prompt_preset, "Saved captioning prompt presets. Built-in presets cannot be deleted."))
        form.addRow("Prompt preset actions", add_help(self.prompt_button_row, "Load, save, remove, or restore the built-in captioning prompt."))
        form.addRow("Captioning prompt", add_help(self.caption_prompt, "Full prompt sent to API, local server, direct local model, or custom command. Supports <trigger>, <profile>, and <template>."))
        form.addRow("Profile suggestion", self.profile_note)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.refresh_local_model_options()
        self.profile.currentTextChanged.connect(self.update_profile_note)
        self.local_model.currentIndexChanged.connect(self.local_model_changed)
        self.api_provider.currentTextChanged.connect(self.refresh_api_model_presets)
        self.local_server_provider.currentTextChanged.connect(self.local_server_provider_changed)
        self.mode.currentTextChanged.connect(self.update_mode_controls)
        self.update_profile_note(self.profile.currentText())
        self.controls_ready = True
        self.update_mode_controls(self.mode.currentText())

    def browse_model_path(self) -> None:
        self.open_model_registry()

    def open_model_registry(self) -> None:
        dialog = ModelRegistryDialog(self.settings, self)
        if dialog.exec():
            preset = self.settings.get("selected_caption_model_preset", "")
            self.refresh_local_model_options()
            self.model_path.setText(self.settings.get("model_path", self.model_path.text()))
            self.profile_note.setText(f"Selected model preset: {preset}" if preset else self.profile_note.text())

    def downloaded_model_entries(self) -> list[dict[str, str]]:
        entries = [dict(item) for item in self.settings.get("caption_model_registry", default_caption_model_registry())]
        return [entry for entry in entries if model_target_downloaded(entry.get("target_folder", ""))]

    def refresh_local_model_options(self) -> None:
        current_name = self.settings.get("selected_caption_model_preset", "")
        current_path = self.settings.get("model_path", "")
        self.local_model.blockSignals(True)
        self.local_model.clear()
        entries = self.downloaded_model_entries()
        if not entries:
            self.local_model.addItem("No downloaded local models", {})
            self.local_model.setEnabled(False)
            if hasattr(self, "model_path"):
                self.model_path.setText("")
            self.local_model.blockSignals(False)
            return
        for entry in entries:
            label = f"{entry.get('name', 'Untitled')}  [{entry.get('backend', 'Local model')}]"
            self.local_model.addItem(label, entry)
        selected = 0
        for index, entry in enumerate(entries):
            if entry.get("name") == current_name or entry.get("target_folder") == current_path:
                selected = index
                break
        self.local_model.setCurrentIndex(selected)
        self.local_model.setEnabled(True)
        self.local_model.blockSignals(False)
        self.local_model_changed(self.local_model.currentIndex())

    def local_model_changed(self, _index: int) -> None:
        entry = self.local_model.currentData()
        if not isinstance(entry, dict):
            self.model_path.setText("")
            return
        self.model_path.setText(entry.get("target_folder", ""))
        self.settings["local_model_type"] = entry.get("backend", "")
        self.settings["model_path"] = entry.get("target_folder", "")
        self.settings["selected_caption_model_preset"] = entry.get("name", "")

    def default_local_server_url(self, provider: str) -> str:
        defaults = {
            "Ollama": "http://localhost:11434/api/generate",
            "LM Studio": "http://localhost:1234/v1/chat/completions",
            "KoboldCPP": "http://localhost:5001/v1/chat/completions",
            "Custom OpenAI-compatible": "http://localhost:1234/v1/chat/completions",
            "Custom JSON": "http://localhost:5000/caption",
        }
        return defaults.get(provider, defaults["Ollama"])

    def local_server_provider_changed(self, provider: str) -> None:
        known_defaults = {self.default_local_server_url(name) for name in LOCAL_SERVER_MODEL_PRESETS}
        if not self.local_server_url.text().strip() or self.local_server_url.text().strip() in known_defaults:
            self.local_server_url.setText(self.default_local_server_url(provider))
        self.refresh_local_server_model_presets(self.local_server_model.currentText().strip())
        self.update_mode_controls(self.mode.currentText())

    def refresh_local_server_model_presets(self, preferred: str = "") -> None:
        current = preferred or self.local_server_model.currentText().strip()
        provider = self.local_server_provider.currentText() if hasattr(self, "local_server_provider") else "Ollama"
        presets = LOCAL_SERVER_MODEL_PRESETS.get(provider, LOCAL_SERVER_MODEL_PRESETS["Ollama"])
        self.local_server_model.blockSignals(True)
        self.local_server_model.clear()
        self.local_server_model.addItems(presets)
        if current:
            if current not in presets:
                self.local_server_model.addItem(current)
            self.local_server_model.setCurrentText(current)
        elif presets:
            self.local_server_model.setCurrentIndex(0)
        self.local_server_model.blockSignals(False)

    def local_server_model_list_url(self) -> str:
        provider = self.local_server_provider.currentText()
        url = self.local_server_url.text().strip()
        if provider == "Ollama":
            return url.replace("/api/generate", "/api/tags").replace("/api/chat", "/api/tags")
        if url.endswith("/chat/completions"):
            return url.rsplit("/chat/completions", 1)[0] + "/models"
        return url.rstrip("/") + "/v1/models"

    def refresh_local_server_models_from_host(self) -> None:
        try:
            request = urllib.request.Request(self.local_server_model_list_url(), method="GET")
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            if self.local_server_provider.currentText() == "Ollama":
                names = [str(item.get("name", "")) for item in data.get("models", []) if item.get("name")]
            else:
                names = [str(item.get("id", "")) for item in data.get("data", []) if item.get("id")]
            if not names:
                raise ValueError("no models returned")
            current = self.local_server_model.currentText().strip()
            self.local_server_model.blockSignals(True)
            self.local_server_model.clear()
            self.local_server_model.addItems(names + ["Custom..."])
            if current and current in names:
                self.local_server_model.setCurrentText(current)
            self.local_server_model.blockSignals(False)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not refresh local server models:\n\n{exc}")

    def load_prompt_presets(self) -> None:
        presets = all_caption_prompt_presets(self.settings)
        selected = self.settings.get("caption_prompt_preset", "Default LoRA Caption")
        self.prompt_preset.blockSignals(True)
        self.prompt_preset.clear()
        self.prompt_preset.addItems(list(presets.keys()))
        if selected in presets:
            self.prompt_preset.setCurrentText(selected)
        self.prompt_preset.blockSignals(False)

    def load_selected_prompt_preset(self) -> None:
        presets = all_caption_prompt_presets(self.settings)
        name = self.prompt_preset.currentText()
        if name in presets:
            self.caption_prompt.setPlainText(presets[name])
            self.settings["caption_prompt_preset"] = name

    def save_current_prompt_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Caption Prompt", "Preset name:", text=self.prompt_preset.currentText() or "My Caption Prompt")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in built_in_caption_prompt_presets():
            QMessageBox.warning(self, APP_NAME, "Built-in prompt presets cannot be overwritten. Save this as a new preset name.")
            return
        self.settings.setdefault("caption_prompt_presets", {})[name] = self.caption_prompt.toPlainText()
        self.settings["caption_prompt_preset"] = name
        self.load_prompt_presets()

    def remove_selected_prompt_preset(self) -> None:
        name = self.prompt_preset.currentText()
        if name in built_in_caption_prompt_presets():
            QMessageBox.information(self, APP_NAME, "Built-in prompt presets cannot be removed.")
            return
        custom = self.settings.setdefault("caption_prompt_presets", {})
        if name in custom and QMessageBox.question(self, APP_NAME, f"Remove caption prompt preset '{name}'?") == QMessageBox.Yes:
            custom.pop(name, None)
            self.settings["caption_prompt_preset"] = "Default LoRA Caption"
            self.load_prompt_presets()
            self.load_selected_prompt_preset()

    def restore_default_prompt_preset(self) -> None:
        self.prompt_preset.setCurrentText("Default LoRA Caption")
        self.load_selected_prompt_preset()

    def update_profile_note(self, profile: str) -> None:
        notes = {
            "Z-Image Base/Turbo": "Suggest Qwen3-VL 8B/4B/2B or an API vision model with natural-language, prompt-like captions. This is only a preset recommendation.",
            "Flux-style LoRA": "Suggest concise natural-language captions with trigger first and visible subject/style details after it.",
            "SDXL character LoRA": "Suggest balanced subject captions with consistent trigger prefix and concrete visual traits.",
            "anime/tag models": "Suggest WD14/tagger-style captions if the training target expects tags.",
            "Unknown/custom": "No strong default; keep all caption/model choices explicit and editable.",
        }
        self.profile_note.setText(notes.get(profile, ""))

    def refresh_api_model_presets(self, preferred: str = "") -> None:
        current = preferred if preferred and preferred not in API_MODEL_PRESETS else self.api_model.currentText().strip()
        provider = self.api_provider.currentText()
        presets = API_MODEL_PRESETS.get(provider, API_MODEL_PRESETS["OpenAI"])
        self.api_model.blockSignals(True)
        self.api_model.clear()
        self.api_model.addItems(presets)
        if current:
            if current not in presets:
                self.api_model.addItem(current)
            self.api_model.setCurrentText(current)
        elif presets:
            self.api_model.setCurrentIndex(0)
        self.api_model.blockSignals(False)
        if getattr(self, "controls_ready", False):
            self.update_mode_controls(self.mode.currentText())

    def set_mode_widget_enabled(self, widget: QWidget, enabled: bool, tooltip: str) -> None:
        widget.setEnabled(enabled)
        widget.setProperty("modeInactive", not enabled)
        widget.setToolTip(tooltip)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        for child in widget.findChildren(QWidget):
            child.setProperty("modeInactive", not enabled)
            child.style().unpolish(child)
            child.style().polish(child)

    def update_mode_controls(self, mode: str) -> None:
        local_enabled = mode == "Local model"
        local_server_enabled = mode == "Local server"
        api_enabled = mode == "API model"
        custom_enabled = mode == "Custom command"
        timeout_enabled = mode in {"Local model", "Local server", "API model", "Custom command"}

        for widget in [self.local_model, self.model_path_row, self.registry_btn, self.device, self.batch]:
            self.set_mode_widget_enabled(widget, local_enabled, "Enabled only when Caption mode is Local model.")
        for widget in [self.local_server_provider, self.local_server_url, self.local_server_model, self.refresh_server_models_btn]:
            self.set_mode_widget_enabled(widget, local_server_enabled, "Enabled only when Caption mode is Local server.")
        for widget in [self.api_provider, self.api_model]:
            self.set_mode_widget_enabled(widget, api_enabled, "Enabled only when Caption mode is API model.")
        self.set_mode_widget_enabled(self.command, custom_enabled, 'Enabled only when Caption mode is Custom command. Use placeholders like "{image}", "{trigger}", and "{prompt}".')
        self.set_mode_widget_enabled(self.timeout, timeout_enabled, "Used by API model, Local command, and Custom command captioning.")
        self.set_mode_widget_enabled(self.json_field, custom_enabled or (api_enabled and self.api_provider.currentText() == "Custom HTTP") or (local_server_enabled and self.local_server_provider.currentText() == "Custom JSON"), "Used for Custom command JSON output, Custom HTTP API responses, or Custom JSON local server responses.")
        if mode == "API model":
            self.mode_note.setText("API mode is active. API provider/model controls are enabled; local model downloads, model path, device, batch, and custom command controls are intentionally disabled.")
        elif mode == "Local model":
            self.mode_note.setText("Local model mode is active. Only downloaded registry models can be selected; API provider/model and custom command controls are intentionally disabled.")
        elif mode == "Local server":
            self.mode_note.setText("Local server mode is active. Ollama, LM Studio, KoboldCPP, or custom local endpoint controls are enabled; direct local model and cloud API controls are intentionally disabled.")
        elif mode == "Custom command":
            self.mode_note.setText("Custom command mode is active. Command, timeout, and JSON parsing controls are enabled; local model and API model controls are intentionally disabled.")
        else:
            self.mode_note.setText("Manual/template mode is active. Backend-specific controls are disabled because no model or API is used.")

    def accept(self) -> None:
        self.settings.update(
            {
                "caption_mode": self.mode.currentText(),
                "training_target_profile": self.profile.currentText(),
                "local_model_type": self.settings.get("local_model_type", ""),
                "model_path": self.model_path.text(),
                "selected_caption_model_preset": self.settings.get("selected_caption_model_preset", ""),
                "device": self.device.currentText(),
                "batch_size": self.batch.value(),
                "local_server_provider": self.local_server_provider.currentText(),
                "local_server_url": self.local_server_url.text().strip(),
                "local_server_model": "" if self.local_server_model.currentText() == "Custom..." else self.local_server_model.currentText().strip(),
                "api_provider": self.api_provider.currentText(),
                "api_model": "" if self.api_model.currentText() == "Custom..." else self.api_model.currentText().strip(),
                "caption_command": self.command.text(),
                "caption_timeout": self.timeout.value(),
                "caption_json_field": self.json_field.text(),
                "caption_template": self.template.toPlainText(),
                "caption_prompt": self.caption_prompt.toPlainText(),
                "caption_prompt_preset": self.prompt_preset.currentText(),
            }
        )
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        DEFAULT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = load_settings()
        self.ensure_default_theme_preset()
        self.settings["folder_preferences"] = clean_folder_preferences(self.settings.get("folder_preferences"))
        self.dataset_root: Path | None = None
        self.manifest: Manifest | EmptyManifest = EmptyManifest()
        self.caption_thread: QThread | None = None
        self.caption_worker: CaptionWorker | None = None
        self.split_thread: QThread | None = None
        self.split_worker: SplitExportWorker | None = None
        self.split_inputs: list[Path] = []
        self.split_outputs: list[Path] = []
        self.split_current: Path | None = None
        self.split_manual_crops: dict[str, list[tuple[int, int, int, int]]] = {}
        self.split_face_crops: dict[str, list[tuple[int, int, int, int]]] = {}
        self.cancel_requested = False
        self.current_dataset_image: Path | None = None
        self.syncing_yaml = False
        self.local_caption_cache: dict[str, Any] = {}
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE}")
        self.resize(1420, 900)
        self.setMinimumSize(1120, 720)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.build_ui()
        self.apply_theme()
        self.refresh_dataset_paths()
        self.refresh_library()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Wheel:
            if isinstance(watched, QAbstractSpinBox):
                event.ignore()
                return True
            if isinstance(watched, QComboBox) and not watched.view().isVisible():
                event.ignore()
                return True
        return super().eventFilter(watched, event)

    def build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("title")
        self.title_label.setTextFormat(Qt.RichText)
        self.update_title_label()
        header.addWidget(self.title_label)
        header.addStretch(1)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        header.addWidget(add_help(settings_btn, "Configure custom library roots and Ostris AI Toolkit path."))
        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self.build_user_tab(), "User")
        self.tabs.addTab(self.build_cut_tab(), "Cut / Split")
        self.tabs.addTab(self.build_dataset_tab(), "Dataset Prep")
        self.tabs.addTab(self.build_library_tab(), "Library")
        self.tabs.addTab(self.build_ostris_tab(), "Ostris Configs / AI Toolkit Presets")
        self.tabs.addTab(self.build_guide_tab(), "Guide")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.status = QLabel("Ready")
        layout.addWidget(self.status)

    def apply_theme(self) -> None:
        t = dict(THEME)
        t.update(self.settings.get("theme", {}))
        progress = self.settings.get("progress_gradient", {})
        start = progress.get("start", t["accent"]) or t["accent"]
        end = progress.get("end", t["accent"]) or t["accent"]
        if progress.get("enabled"):
            progress_fill = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"
        else:
            progress_fill = t["accent"]
        self.update_title_label(t)
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {t['bg']}; color: {t['text']}; font-family: Inter, "Segoe UI Variable", "Segoe UI", Arial; font-size: 10pt; }}
            QLabel {{ color: {t['text']}; background: transparent; }}
            QLabel#title {{ font-size: 14pt; font-weight: 700; }}
            QGroupBox {{ border: 1px solid {t['border']}; border-radius: 8px; margin-top: 12px; padding: 10px; background: {t['panel']}; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {t['muted']}; }}
            QPushButton, QToolButton {{ background: {t['button']}; color: {t['text']}; border: 1px solid {t['border']}; padding: 7px 10px; border-radius: 8px; }}
            QPushButton:hover, QToolButton:hover {{ background: {t['button_active']}; border-color: #3a3a3a; }}
            QPushButton:pressed, QToolButton:pressed {{ background: {t['field']}; border-color: {t['accent']}; }}
            QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QSpinBox, QComboBox {{ background: {t['field']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 5px; selection-background-color: {t['accent']}; selection-color: #101010; }}
            QPushButton:disabled, QToolButton:disabled, QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
                background: #080808;
                color: #555555;
                border: 1px dashed #3a3a3a;
            }}
            QWidget[modeInactive="true"] QLineEdit,
            QWidget[modeInactive="true"] QComboBox,
            QWidget[modeInactive="true"] QPushButton,
            QComboBox[modeInactive="true"],
            QLineEdit[modeInactive="true"],
            QSpinBox[modeInactive="true"],
            QPushButton[modeInactive="true"] {{
                background: #070707;
                color: #4f4f4f;
                border: 1px dashed #444444;
            }}
            QListWidget::item:selected {{ background: {t['accent']}; color: #101010; border: 1px solid {t['accent']}; border-radius: 6px; }}
            QListWidget::item:hover {{ background: {t['button_active']}; border-radius: 6px; }}
            QTabWidget::pane {{ border: 1px solid {t['border']}; border-radius: 8px; top: -1px; }}
            QTabBar::tab {{ background: {t['panel']}; color: {t['muted']}; border: 1px solid {t['border']}; padding: 8px 12px; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            QTabBar::tab:selected {{ background: {t['button_active']}; color: {t['text']}; border-bottom-color: {t['button_active']}; }}
            QCheckBox {{ spacing: 8px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {t['border']}; border-radius: 3px; background: {t['field']}; }}
            QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; }}
            QSplitter::handle {{ background: {t['bg']}; }}
            QMenu {{ background: {t['panel']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['button_active']}; }}
            QProgressBar {{ background: {t['field']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 2px; text-align: center; min-height: 16px; }}
            QProgressBar::chunk {{ background: {progress_fill}; border-radius: 6px; }}
            """
        )
        for widget in self.findChildren(DropListWidget):
            widget.set_accent_color(t["accent"])
        for widget in self.findChildren(ImagePreview):
            widget.set_accent_color(t["accent"])

    def begin_progress(self, label: str, maximum: int) -> None:
        if not hasattr(self, "progress_bar"):
            return
        self.progress_bar.setRange(0, max(1, maximum))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{label} %p%")
        self.progress_bar.setVisible(True)
        self.status.setText(label)
        if QThread.currentThread() == QApplication.instance().thread():
            QApplication.processEvents()

    def update_progress(self, value: int, label: str | None = None) -> None:
        if not hasattr(self, "progress_bar"):
            return
        self.progress_bar.setValue(value)
        if label:
            self.status.setText(label)
        if QThread.currentThread() == QApplication.instance().thread():
            QApplication.processEvents()

    def end_progress(self, label: str = "") -> None:
        if not hasattr(self, "progress_bar"):
            return
        self.progress_bar.setValue(self.progress_bar.maximum())
        if label:
            self.status.setText(label)
        if QThread.currentThread() == QApplication.instance().thread():
            QApplication.processEvents()
        self.progress_bar.setVisible(False)

    def folder_preferences(self) -> dict[str, str]:
        prefs = clean_folder_preferences(self.settings.get("folder_preferences"))
        self.settings["folder_preferences"] = prefs
        return prefs

    def folder_rel(self, key: str) -> str:
        return self.folder_preferences().get(key, DEFAULT_FOLDER_PREFERENCES[key])

    def project_folder(self, key: str, root: Path | None = None) -> Path:
        project_root = root or self.dataset_root or DEFAULT_DATASETS_DIR
        return project_root / self.folder_rel(key)

    def current_prepped_folder(self, root: Path | None = None) -> Path:
        project_root = root or self.dataset_root or DEFAULT_DATASETS_DIR
        manifest = self.manifest if project_root == self.dataset_root else Manifest(project_root)
        configured = self.project_folder("export", project_root)
        folder = manifest.data.get("export", {}).get("folder", "")
        if folder:
            candidate = Path(folder)
            if candidate.exists():
                return candidate
        return configured

    def build_user_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        intro = QLabel("Set the relative folder names PrepMI-PrepYU should use inside each project. Defaults match the current structure.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        group = QGroupBox("Project Folder Structure")
        form = QFormLayout(group)
        self.folder_pref_edits: dict[str, QLineEdit] = {}
        prefs = self.folder_preferences()
        for key in DEFAULT_FOLDER_PREFERENCES:
            edit = QLineEdit(prefs[key])
            edit.setPlaceholderText(DEFAULT_FOLDER_PREFERENCES[key])
            self.folder_pref_edits[key] = edit
            form.addRow(
                FOLDER_PREFERENCE_LABELS[key],
                add_help(edit, "Relative folder path inside each project. Nested folders are allowed. Absolute paths and '..' are ignored."),
            )
        layout.addWidget(group)

        actions = QHBoxLayout()
        save_btn = QPushButton("Save Folder Preferences")
        reset_btn = QPushButton("Restore Defaults")
        repair_btn = QPushButton("Create/Repair Current Project")
        save_btn.clicked.connect(self.save_folder_preferences_from_user_tab)
        reset_btn.clicked.connect(self.reset_folder_preferences)
        repair_btn.clicked.connect(self.ensure_dataset_structure)
        actions.addWidget(add_help(save_btn, "Save these folder names and use them immediately across the app."))
        actions.addWidget(add_help(reset_btn, "Reset folder names to the original PrepMI-PrepYU structure."))
        actions.addWidget(add_help(repair_btn, "Create missing folders in the currently selected project using these preferences."))
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)
        scroll.setWidget(panel)
        return tab

    def save_folder_preferences_from_user_tab(self) -> None:
        raw = {key: edit.text() for key, edit in getattr(self, "folder_pref_edits", {}).items()}
        prefs = clean_folder_preferences(raw)
        self.settings["folder_preferences"] = prefs
        for key, value in prefs.items():
            if key in self.folder_pref_edits:
                self.folder_pref_edits[key].setText(value)
        save_settings(self.settings)
        if self.dataset_root is not None:
            self.ensure_dataset_structure(save=False)
            self.load_current_dataset_images()
            self.refresh_anchors()
            self.refresh_library()
            self.update_split_project_label()
        self.status.setText("Folder preferences saved")

    def reset_folder_preferences(self) -> None:
        self.settings["folder_preferences"] = dict(DEFAULT_FOLDER_PREFERENCES)
        for key, value in DEFAULT_FOLDER_PREFERENCES.items():
            if hasattr(self, "folder_pref_edits") and key in self.folder_pref_edits:
                self.folder_pref_edits[key].setText(value)
        save_settings(self.settings)
        self.status.setText("Folder preferences restored to defaults")

    def request_cancel(self) -> None:
        self.cancel_requested = True
        if self.caption_worker is not None:
            self.caption_worker.request_cancel()
        if self.split_worker is not None:
            self.split_worker.request_cancel()
        self.status.setText("Stopping after the current item...")
        QApplication.processEvents()

    def update_title_label(self, theme: dict[str, str] | None = None) -> None:
        if not hasattr(self, "title_label"):
            return
        t = dict(THEME)
        t.update(self.settings.get("theme", {}))
        if theme:
            t.update(theme)
        accent = t["accent"]
        text = (
            f"Prep<span style='color:{accent};'>MI</span>-Prep<span style='color:{accent};'>YU</span>"
            f" &nbsp;|&nbsp; "
            f"<span style='color:{accent};'>D</span>ataset "
            f"<span style='color:{accent};'>P</span>rep "
            f"<span style='color:{accent};'>S</span>tudio"
        )
        self.title_label.setText(text)

    def save_theme_preset(self, name: str, theme: dict[str, str]) -> None:
        presets = self.settings.setdefault("theme_presets", {})
        presets[name] = theme
        save_settings(self.settings)

    def ensure_default_theme_preset(self) -> None:
        presets = self.settings.setdefault("theme_presets", {})
        changed = False
        for name, theme in built_in_theme_presets().items():
            if name not in presets:
                presets[name] = theme
                changed = True
        if changed:
            save_settings(self.settings)

    def apply_theme_values(self, theme: dict[str, str]) -> None:
        clean = {key: value.strip() for key, value in theme.items() if key in THEME and value.strip()}
        self.settings["theme"] = clean
        save_settings(self.settings)
        self.apply_theme()

    def build_cut_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        project_row = QHBoxLayout()
        self.split_project_label = QLabel("Project: none")
        scan_project = QPushButton("Scan Project Sheets")
        load_project = QPushButton("Load Project Images")
        scan_project.clicked.connect(self.scan_project_sheets)
        load_project.clicked.connect(self.load_project_images_for_split)
        project_row.addWidget(self.split_project_label, 1)
        project_row.addWidget(add_help(load_project, "Load all images from the current project's configured image folder into Cut / Split."))
        project_row.addWidget(add_help(scan_project, "Auto-detect likely image sheets in the current project's configured image folder and queue only those."))
        layout.addLayout(project_row)
        toolbar = QHBoxLayout()
        for text, slot, tip in [
            ("Load Images", self.load_split_images, "Load one or more image sheets."),
            ("Load Folder", self.load_split_folder, "Load all images from a folder."),
            ("Auto Detect", self.detect_split_grid, "Guess rows and columns for the selected image."),
            ("Preview Cuts", self.preview_split_cuts, "Refresh the grid overlay and cut summary before export."),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            toolbar.addWidget(add_help(button, tip))
        self.split_play_button = QToolButton()
        self.split_play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.split_play_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.split_play_button.setText("Export")
        self.split_play_button.clicked.connect(self.export_split_cuts)
        self.split_stop_button = QToolButton()
        self.split_stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.split_stop_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.split_stop_button.setText("Stop")
        self.split_stop_button.setEnabled(False)
        self.split_stop_button.clicked.connect(self.request_cancel)
        toolbar.addWidget(add_help(self.split_play_button, "Start exporting cuts for the loaded sheets/images."))
        toolbar.addWidget(add_help(self.split_stop_button, "Stop the current export after the current file/crop finishes. Already exported files are kept."))
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.split_preview = ImagePreview("Load image sheets to preview cut lines.")
        self.split_preview.crop_drawn.connect(self.add_manual_crop_box)
        self.split_preview.crop_changed.connect(self.update_manual_crop_box)
        self.split_preview.crop_removed.connect(self.clear_manual_crops_for_current)
        self.split_preview.boxes_changed.connect(self.update_current_crop_boxes)
        left_layout.addWidget(self.split_preview, 1)
        self.split_info = QLabel("No image selected")
        self.split_info.setWordWrap(True)
        left_layout.addWidget(self.split_info)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        controls = QGroupBox("Cut Controls")
        form = QFormLayout(controls)
        form.setContentsMargins(14, 10, 14, 10)
        form.setVerticalSpacing(5)
        self.cut_controls_form = form
        self.cut_mode = QComboBox()
        self.cut_mode.addItems(["Grid / Sheet", "Face crops", "Manual crops"])
        self.cut_mode.currentTextChanged.connect(self.cut_mode_changed)
        self.split_rows = QSpinBox()
        self.split_rows.setRange(1, 64)
        self.split_rows.setValue(2)
        self.split_cols = QSpinBox()
        self.split_cols.setRange(1, 64)
        self.split_cols.setValue(2)
        self.crop_left = QSpinBox()
        self.crop_top = QSpinBox()
        self.crop_right = QSpinBox()
        self.crop_bottom = QSpinBox()
        for spin in [self.crop_left, self.crop_top, self.crop_right, self.crop_bottom]:
            spin.setRange(0, 20000)
            spin.valueChanged.connect(self.preview_split_cuts)
        self.auto_detect = QCheckBox("Auto-detect per image")
        self.auto_detect.setChecked(True)
        self.face_detector = QComboBox()
        self.face_detector.addItems(["OpenCV Haar"])
        self.face_framing = QComboBox()
        self.face_framing.addItems(["Face tight", "Head", "Head and shoulders", "Square portrait"])
        self.face_framing.setCurrentText("Head and shoulders")
        self.face_padding = QSpinBox()
        self.face_padding.setRange(0, 300)
        self.face_padding.setSuffix("%")
        self.face_padding.setValue(80)
        self.face_min_size = QSpinBox()
        self.face_min_size.setRange(8, 2000)
        self.face_min_size.setValue(48)
        self.face_confidence = QSpinBox()
        self.face_confidence.setRange(1, 99)
        self.face_confidence.setSuffix("%")
        self.face_confidence.setValue(50)
        detect_faces = QPushButton("Detect Faces")
        detect_faces.clicked.connect(self.detect_faces_for_current)
        detect_all_faces = QPushButton("Detect All Loaded")
        detect_all_faces.clicked.connect(self.detect_faces_for_all)
        face_actions = QHBoxLayout()
        face_actions.setContentsMargins(0, 0, 0, 0)
        face_actions.addWidget(detect_faces)
        face_actions.addWidget(detect_all_faces)
        self.face_actions_row = QWidget()
        self.face_actions_row.setLayout(face_actions)
        self.manual_crop_list = QListWidget()
        self.manual_crop_list.setMaximumHeight(54)
        self.manual_crop_list.currentRowChanged.connect(lambda _row: self.preview_split_cuts())
        self.crop_ratio = QComboBox()
        self.crop_ratio.addItems(["Free", "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"])
        self.crop_ratio.setCurrentText("1:1")
        self.crop_ratio.currentTextChanged.connect(self.crop_ratio_changed)
        delete_crop = QPushButton("Delete Selected Crop")
        clear_crops = QPushButton("Clear Crops For Image")
        delete_crop.clicked.connect(self.delete_selected_manual_crop)
        clear_crops.clicked.connect(self.clear_manual_crops_for_current)
        manual_actions = QHBoxLayout()
        manual_actions.setContentsMargins(0, 0, 0, 0)
        manual_actions.addWidget(delete_crop)
        manual_actions.addWidget(clear_crops)
        self.manual_actions_row = QWidget()
        self.manual_actions_row.setLayout(manual_actions)
        self.split_resize = QCheckBox("Resize final export copy")
        self.split_resize_preset = QComboBox()
        self.split_resize_preset.addItems([f"{size}x{size}" for size in range(256, 2049, 256)] + ["Custom"])
        self.split_resize_preset.setCurrentText("1024x1024")
        self.split_resize_custom = QLineEdit("1024x1024")
        self.split_resize_custom.setPlaceholderText("WIDTHxHEIGHT")
        resize_row = QHBoxLayout()
        resize_row.setContentsMargins(0, 0, 0, 0)
        resize_row.addWidget(self.split_resize_preset, 1)
        resize_row.addWidget(self.split_resize_custom, 1)
        self.split_resize_row = QWidget()
        self.split_resize_row.setLayout(resize_row)
        self.naming_pattern = QComboBox()
        self.naming_pattern.addItems(["{source_name}_{row}_{col}.png", "{source_name}_{index}.png", "{source_name}_{mode}_{index}.png", "{source_name}_crop_{index}.png"])
        self.split_output = QLineEdit("")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_split_output)
        out_row = QHBoxLayout()
        out_row.addWidget(self.split_output, 1)
        out_row.addWidget(browse)
        form.addRow("Cut mode", add_help(self.cut_mode, "Choose grid splitting, automatic face crop suggestions, or draw manual crop boxes on the preview."))
        form.addRow("Rows", add_help(self.split_rows, "Number of grid rows."))
        form.addRow("Columns", add_help(self.split_cols, "Number of grid columns/frames."))
        form.addRow("Crop left px", add_help(self.crop_left, "Trim this many pixels from the left before cutting."))
        form.addRow("Crop top px", add_help(self.crop_top, "Trim this many pixels from the top before cutting."))
        form.addRow("Crop right px", add_help(self.crop_right, "Trim this many pixels from the right before cutting."))
        form.addRow("Crop bottom px", add_help(self.crop_bottom, "Trim this many pixels from the bottom before cutting."))
        form.addRow(add_help(self.auto_detect, "When enabled, each image gets its own guessed row/column layout."))
        form.addRow("Detector", add_help(self.face_detector, "Local face detector backend. OpenCV Haar is used when cv2 is installed."))
        form.addRow("Face framing", add_help(self.face_framing, "How much context to include around detected faces."))
        form.addRow("Face padding", add_help(self.face_padding, "Extra crop padding around detected faces before framing is applied."))
        form.addRow("Min face size", add_help(self.face_min_size, "Ignore detections smaller than this many pixels."))
        form.addRow("Confidence", add_help(self.face_confidence, "Reserved for stronger detectors; OpenCV Haar does not provide per-face confidence."))
        form.addRow(add_help(self.face_actions_row, "Detect face boxes for the selected image or all loaded images, then review before export."))
        form.addRow("Manual crops", add_help(self.manual_crop_list, "Draw boxes on the preview. Select a crop here to inspect or delete it."))
        form.addRow("Crop ratio", add_help(self.crop_ratio, "Constrain manual crop boxes and face-detected crop boxes to this aspect ratio."))
        form.addRow(add_help(self.manual_actions_row, "Delete or clear manual crops for the selected source image."))
        form.addRow(add_help(self.split_resize, "Keep split files at their original crop size. Resize only the copy that goes to the final export/prepped folder."))
        form.addRow("Final export target", add_help(self.split_resize_row, "Choose the resize target for the final export/prepped copy. The split folder keeps original crop dimensions."))
        form.addRow("Naming pattern", add_help(self.naming_pattern, "Controls exported cell filenames."))
        form.addRow("Output folder", out_row)
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        controls_scroll.setWidget(controls)
        controls_scroll.setMinimumHeight(360)
        controls_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_layout.addWidget(controls_scroll, 1)
        self.split_list = DropListWidget("Drop image sheets here or click Load Images.")
        self.split_list.setViewMode(QListView.IconMode)
        self.split_list.setMovement(QListView.Static)
        self.split_list.setWrapping(True)
        self.split_list.setUniformItemSizes(True)
        self.split_list.setProperty("selection_tint_icon_rect", True)
        self.split_list.setSpacing(SPLIT_THUMB_SPACING)
        self.split_list.setGridSize(QSize(SPLIT_THUMB_TILE, SPLIT_THUMB_TILE))
        self.split_list.setIconSize(QSize(SPLIT_THUMB_ICON, SPLIT_THUMB_ICON))
        self.split_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.split_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.split_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        split_row_step = SPLIT_THUMB_TILE + SPLIT_THUMB_SPACING
        self.split_list.verticalScrollBar().setSingleStep(split_row_step)
        self.split_list.verticalScrollBar().setPageStep(split_row_step * 2)
        self.split_list.setFixedHeight((SPLIT_THUMB_TILE * 2) + (SPLIT_THUMB_SPACING * 3) + 12)
        self.split_list.files_dropped.connect(lambda paths: self.add_split_paths(paths))
        self.split_list.empty_clicked.connect(self.load_split_images)
        self.split_list.currentItemChanged.connect(self.split_selection_changed)
        right_layout.addWidget(QLabel("Loaded sheets"))
        right_layout.addWidget(self.split_list)
        self.split_log = QPlainTextEdit()
        self.split_log.setReadOnly(True)
        self.split_log.setMinimumHeight(48)
        self.split_log.setMaximumHeight(74)
        right_layout.addWidget(QLabel("Split log"))
        right_layout.addWidget(self.split_log)
        splitter.addWidget(right)
        splitter.setSizes([860, 500])
        self.split_rows.valueChanged.connect(self.preview_split_cuts)
        self.split_cols.valueChanged.connect(self.preview_split_cuts)
        self.cut_mode_changed(self.cut_mode.currentText())
        return tab

    def build_dataset_tab(self) -> QWidget:
        tab = ProjectDropWidget()
        tab.project_dropped.connect(self.handle_project_folder_drop)
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self.dataset_root_edit = QLineEdit("")
        self.dataset_root_edit.editingFinished.connect(self.dataset_root_edited)
        self.project_combo = QComboBox()
        self.project_combo.addItem("Available projects...", "")
        self.project_combo.currentIndexChanged.connect(self.project_combo_changed)
        browse = QPushButton("Select Project")
        create = QPushButton("Create/Repair")
        rename = QPushButton("Rename Project")
        delete = QPushButton("Delete Project")
        load = QPushButton("Load Prepped Images")
        source = QPushButton("Load Source Folder")
        browse.clicked.connect(self.choose_dataset_root)
        create.clicked.connect(self.ensure_dataset_structure)
        rename.clicked.connect(self.rename_dataset)
        delete.clicked.connect(self.delete_dataset)
        load.clicked.connect(self.load_current_dataset_images)
        source.clicked.connect(self.load_dataset_source_folder)
        top.addWidget(QLabel("Project folder"))
        top.addWidget(add_help(self.dataset_root_edit, "Project folder. Empty until you create or select a project."), 1)
        top.addWidget(add_help(self.project_combo, "Select a known project from the app-managed projects folder or custom project roots."), 1)
        for button, tip in [
            (browse, "Choose a project folder."),
            (create, "Create the expected project folder structure. If blank, you will be asked for a project name."),
            (rename, "Rename the selected project folder and update its manifest."),
            (delete, "Delete the selected project only if it is inside a configured project root. Outside folders are refused for safety."),
            (load, "Load images from the current prepped/final dataset folder."),
            (source, "Load images from any user-selected folder."),
        ]:
            top.addWidget(add_help(button, tip))
        layout.addLayout(top)

        quick = QHBoxLayout()
        self.caption_mode = QComboBox()
        self.caption_mode.addItems(["Manual / Template only", "Local model", "Local server", "API model", "Custom command"])
        self.caption_mode.setCurrentText(self.manifest.data.get("caption_mode", "Manual / Template only"))
        self.trigger_edit = QLineEdit(self.manifest.data.get("trigger", ""))
        caption_settings = QPushButton("Caption Settings")
        generate = QPushButton("Generate Captions")
        validate = QPushButton("Validate Everything")
        export = QPushButton("Export Final Dataset")
        caption_settings.clicked.connect(self.open_caption_settings)
        generate.clicked.connect(self.generate_captions)
        validate.clicked.connect(self.validate_dataset)
        export.clicked.connect(self.export_dataset)
        quick.addWidget(QLabel("Caption mode"))
        quick.addWidget(add_help(self.caption_mode, "Quick caption mode selection; detailed backend setup lives in Caption Settings."))
        quick.addWidget(QLabel("Trigger token"))
        quick.addWidget(add_help(self.trigger_edit, "Required. Generated captions start with this exact token followed by a comma."), 1)
        for button, tip in [(caption_settings, "Configure manual, local, API, or custom command captioning."), (generate, "Generate captions for selected prepped images."), (validate, "Run image/caption/integrity checks on the current prepped folder."), (export, "Apply the selected resize settings to the current final export/prepped folder.")]:
            quick.addWidget(add_help(button, tip))
        layout.addLayout(quick)

        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.dataset_list = DropListWidget("Load a project to show prepped images here.", 96)
        self.dataset_list.files_dropped.connect(self.handle_dataset_drop)
        self.dataset_list.currentItemChanged.connect(self.dataset_selection_changed)
        self.dataset_list.setSelectionMode(QListWidget.ExtendedSelection)
        left_layout.addWidget(self.dataset_list, 1)
        buttons = QGridLayout()
        actions = [
            ("Reject", lambda: self.classify_selected("rejected"), "Move/copy selected images to the configured rejected folder."),
            ("0.use", lambda: self.classify_selected("broad"), "Broad usable set."),
            ("0.useV2", lambda: self.classify_selected("strict"), "Strict LoRA-ready set."),
            ("Variant/Optional", lambda: self.classify_selected("Variant/Optional"), "Mark as optional variant without exporting as strict."),
            ("Needs Review", lambda: self.classify_selected("Needs Review"), "Mark for later review."),
            ("Contact Sheet", self.make_contact_sheet, "Create a contact sheet from current/selected images."),
        ]
        for index, (text, slot, tip) in enumerate(actions):
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(add_help(button, tip), index // 3, index % 3)
        left_layout.addLayout(buttons)
        split.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        compare_row = QHBoxLayout()
        compare_row.setContentsMargins(0, 0, 0, 0)
        compare_row.setSpacing(10)
        selected_box = QWidget()
        selected_layout = QVBoxLayout(selected_box)
        selected_layout.setContentsMargins(0, 0, 0, 0)
        selected_layout.setSpacing(4)
        selected_label = QLabel("Selected image")
        selected_label.setAlignment(Qt.AlignCenter)
        self.dataset_preview = ImagePreview("Select an image to review.")
        self.dataset_preview.setMinimumSize(260, 220)
        self.dataset_preview.setMaximumHeight(360)
        selected_layout.addWidget(selected_label)
        selected_layout.addWidget(self.dataset_preview, 1)
        anchor_box = QWidget()
        anchor_layout = QVBoxLayout(anchor_box)
        anchor_layout.setContentsMargins(0, 0, 0, 0)
        anchor_layout.setSpacing(4)
        anchor_label = QLabel("Anchor")
        anchor_label.setAlignment(Qt.AlignCenter)
        self.anchor_preview = ImagePreview("Optional anchor/reference comparison.")
        self.anchor_preview.setMinimumSize(260, 220)
        self.anchor_preview.setMaximumHeight(360)
        anchor_layout.addWidget(anchor_label)
        anchor_layout.addWidget(self.anchor_preview, 1)
        compare_row.addWidget(selected_box, 1)
        compare_row.addWidget(anchor_box, 1)
        right_layout.addLayout(compare_row, 1)
        anchor_row = QHBoxLayout()
        self.anchor_combo = QComboBox()
        choose_anchor = QPushButton("Add Anchor")
        choose_anchor.clicked.connect(self.add_anchor)
        self.anchor_combo.currentTextChanged.connect(self.show_anchor)
        anchor_row.addWidget(QLabel("Anchor"))
        anchor_row.addWidget(add_help(self.anchor_combo, "Optional reference image from the configured anchors folder for side-by-side comparison."), 1)
        anchor_row.addWidget(add_help(choose_anchor, "Copy an anchor/reference image into the configured anchors folder."))
        right_layout.addLayout(anchor_row)
        self.reason_tags = QLineEdit("")
        self.reason_tags.setPlaceholderText("weak likeness, bad crop, duplicate, expression too extreme, style drift, variant hair, good anchor")
        self.caption_editor = QPlainTextEdit()
        self.caption_editor.setPlaceholderText("Caption for selected image. Captions must start with <trigger>, exactly.")
        save_caption = QPushButton("Save Caption / Tags")
        save_caption.clicked.connect(self.save_caption_for_current)
        right_layout.addWidget(QLabel("Reason tags"))
        right_layout.addWidget(add_help(self.reason_tags, "Comma-separated tags explaining classification choices."))
        right_layout.addWidget(QLabel("Caption editor"))
        right_layout.addWidget(add_help(self.caption_editor, "Manual caption editor for the selected image."))
        right_layout.addWidget(add_help(save_caption, "Save caption and reason tags to sidecar txt and manifest."))
        export_box = QGroupBox("Export Resize")
        form = QFormLayout(export_box)
        self.export_size = QComboBox()
        self.export_size.addItems(["512x512", "768x768", "1024x1024", "1536x1536", "Original", "Custom"])
        self.export_size.setCurrentText(self.manifest.data.get("export", {}).get("size", "1024x1024"))
        self.custom_export_size = QLineEdit("1024x1024")
        self.resize_mode = QComboBox()
        self.resize_mode.addItems(["Stretch to exact size", "Fit inside and pad", "Center crop", "Keep aspect ratio"])
        self.resize_mode.setCurrentText(self.manifest.data.get("export", {}).get("resize_mode", "Keep aspect ratio"))
        form.addRow("Final image size", add_help(self.export_size, "Final export target; choose Custom to type any WIDTHxHEIGHT."))
        form.addRow("Custom size", add_help(self.custom_export_size, "Used only when Final image size is Custom."))
        form.addRow("Resize mode", add_help(self.resize_mode, "How split images are resized when creating the prepped folder."))
        right_layout.addWidget(export_box)
        split.addWidget(right)
        split.setSizes([580, 820])
        return tab

    def build_library_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        bar = QHBoxLayout()
        refresh = QPushButton("Refresh")
        add_root = QPushButton("Add Custom Root")
        refresh.clicked.connect(self.refresh_library)
        add_root.clicked.connect(self.add_custom_root)
        bar.addWidget(QLabel("Scans app-managed projects plus user-added project roots only."))
        bar.addStretch(1)
        bar.addWidget(refresh)
        bar.addWidget(add_root)
        layout.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.library_list = QListWidget()
        self.library_list.currentItemChanged.connect(self.library_selection_changed)
        self.library_list.itemDoubleClicked.connect(lambda _: self.open_library_dataset())
        left_layout.addWidget(add_help(self.library_list, "Known projects. Selecting one shows its manifest and prepped thumbnails. Double-click to open in Dataset Prep."), 1)
        split.addWidget(left)

        detail_split = QSplitter(Qt.Horizontal)
        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        self.library_summary = QLabel("Select a project to inspect.")
        self.library_summary.setWordWrap(True)
        middle_layout.addWidget(self.library_summary)
        self.library_thumbs = DropListWidget("Select a project to show prepped thumbnails.", 128)
        self.library_thumbs.setViewMode(QListView.IconMode)
        self.library_thumbs.setMovement(QListView.Static)
        self.library_thumbs.setWrapping(True)
        self.library_thumbs.setUniformItemSizes(True)
        self.library_thumbs.setSpacing(8)
        self.library_thumbs.setGridSize(QSize(138, 138))
        self.library_thumbs.setIconSize(QSize(128, 128))
        self.library_thumbs.currentItemChanged.connect(self.library_thumbnail_changed)
        middle_layout.addWidget(QLabel("Prepped thumbnails"))
        middle_layout.addWidget(self.library_thumbs, 1)
        self.library_preview = ImagePreview("Select a prepped thumbnail to preview.")
        self.library_preview.setMinimumHeight(260)
        middle_layout.addWidget(self.library_preview, 1)
        detail_split.addWidget(middle)

        manifest_box = QWidget()
        manifest_layout = QVBoxLayout(manifest_box)
        manifest_layout.addWidget(QLabel("Manifest"))
        self.library_manifest_view = QPlainTextEdit()
        self.library_manifest_view.setReadOnly(True)
        self.library_manifest_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        manifest_layout.addWidget(add_help(self.library_manifest_view, "Read-only manifest.json preview for the selected project."), 1)
        detail_split.addWidget(manifest_box)
        detail_split.setSizes([650, 520])
        split.addWidget(detail_split)
        split.setSizes([430, 970])

        actions = QHBoxLayout()
        for text, slot, tip in [
            ("Open Project", self.open_library_dataset, "Open selected project in Dataset Prep."),
            ("Open Split", lambda: self.open_library_folder_key("split"), "Open configured split folder."),
            ("Open 0.useV2", lambda: self.open_library_folder_key("strict"), "Open configured strict set folder."),
            ("Open 0.Prepped", lambda: self.open_library_folder_key("export"), "Open configured final export folder."),
            ("Re-run Validation", self.validate_library_dataset, "Run validation on selected library item."),
            ("Edit Manifest", self.edit_library_manifest, "Open manifest.json in the default editor."),
            ("Archive/Hide", self.hide_library_dataset, "Hide selected project from the library list."),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            actions.addWidget(add_help(button, tip))
        actions.addStretch(1)
        layout.addLayout(actions)
        return tab

    def build_guide_tab(self) -> QWidget:
        text = QTextBrowser()
        text.setReadOnly(True)
        text.setOpenLinks(False)
        text.setOpenExternalLinks(False)
        text.anchorClicked.connect(self.open_guide_image)
        def guide_img(name: str, alt: str) -> str:
            path = GUIDE_ASSET_DIR / name
            if not path.exists():
                return f"<p><i>{alt} screenshot will appear here after guide assets are generated.</i></p>"
            thumb = guide_thumbnail_path(path) or path
            return f"<p><a href='{path.as_uri()}'><img src='{thumb.as_uri()}' width='920'></a><br><i>{alt} Click the screenshot or the + badge to open it full size.</i></p>"

        guide_html = f"""
            <style>
              body {{ line-height: 1.35; }}
              h2 {{ margin-top: 18px; }}
              h3 {{ margin-top: 14px; }}
              code {{ background: #222; padding: 2px 4px; }}
              table {{ border-collapse: collapse; }}
              td, th {{ border: 1px solid #555; padding: 5px 8px; }}
            </style>
            <h1>PrepMI-PrepYU Guide</h1>
            <p><b>Short version:</b> this app is for turning messy image folders and sheets into a LoRA-ready project. Pick or import a project, split what needs splitting, let split export fill the prepped folder, caption those actual prepped files, validate them, then make an Ostris config you can manually load in AI Toolkit.</p>

            {guide_img("dataset_prep.png", "Dataset Prep: project selection, review grid, preview, captions, and export controls.")}

            <h2>User</h2>
            {guide_img("user.png", "User: configurable project folder structure preferences.")}
            <p>The <b>User</b> tab is where you set your preferred project folder names. Keep the defaults if you like the current PrepMI-PrepYU structure, or change the relative paths for project images, split output, broad picks, strict picks, rejected images, anchors, and final export. After saving, <b>Create/Repair Current Project</b> creates any missing folders using those names.</p>

            <h2>Project Folders</h2>
            <p>A project is the top-level folder. By default, the app uses this shape:</p>
            <pre>anchors\\
dataset\\
dataset\\split\\
1.Prep\\0.use\\
1.Prep\\0.useV2\\
0.Prepped\\
rejected\\
manifest.json</pre>
            <p>You can select a project with <b>Select Project</b>, pick one from <b>Available projects</b>, or just drag a folder onto the Dataset Prep tab. If the dropped folder already lives under the app's <code>datasets\\</code> folder, PrepMI-PrepYU opens it. If it is outside that folder, the app copies it into <code>datasets\\</code>, creates the configured folders, creates/repairs the manifest, and loads the current prepped folder.</p>
            <p>The important bit: the project image folder is for raw/source images. <b>Dataset Prep</b> shows the prepped images that will actually get captions. Different thing. Past-us made that confusing; current-us is trying to be less rude about it.</p>
            <p><b>Deletion safety:</b> the app refuses to delete folders outside the configured project roots. Imported outside folders are copied into the app-managed project area first, and the app only deletes the managed copy. If something lives outside those roots, use <b>Archive/Hide</b> or remove it manually.</p>

            <h2>Cut / Split</h2>
            {guide_img("cut_split.png", "Cut / Split: sheet grid, preview, cut controls, progress, and play/stop export controls.")}
            <p>Use this tab when you have sheets, grids, contact sheets, or images that need face/manual crops before review.</p>
            <h3>Grid / Sheet</h3>
            <p><b>Grid / Sheet</b> is the classic splitter. Load images or a folder, use <b>Auto Detect</b> to guess rows/columns, then preview and export. Output defaults to your configured split folder when using the selected project, or a nearby split-style folder when you load loose files.</p>
            <h3>Face crops</h3>
            <p><b>Face crops</b> uses local OpenCV face detection. Pick a crop ratio first if you want the detected boxes normalized to <code>1:1</code>, <code>2:3</code>, <code>3:4</code>, and so on. Click <b>Detect Faces</b> for the current image or <b>Detect All Loaded</b> for the queue. The app draws suggested boxes; you can drag them around or resize them from the corner points before export. Nothing gets sent to an API for this.</p>
            <h3>Manual crops</h3>
            <p><b>Manual crops</b> lets you draw one box per image. Choose a box ratio first, like <code>1:1</code>, <code>2:3</code>, <code>3:4</code>, or <code>Free</code>. Drag on the preview to create the box. After the box exists, drag inside it to move it. Right-click inside it to delete it. Clicking outside the existing box does not create a second box, because mystery duplicate crops are how trust issues start.</p>
            <p>The Play-style <b>Export</b> button starts cutting. <b>Stop</b> cancels the running export after the current crop/source step. Already exported files stay where they are.</p>

            <h2>Dataset Prep</h2>
            <p>This is the prepped-dataset workbench. By default it shows the configured final/prepped folder, usually <code>0.Prepped\\</code>. Those are the images that get captions.</p>
            <p>The usual flow is:</p>
            <ol>
              <li>Put raw sheets and source images in the configured source folder. Default: <code>dataset\\</code>.</li>
              <li>Cut/split source images into the configured split folder. Default: <code>dataset\\split\\</code>.</li>
              <li>Run Cut / Split export to copy split images into the configured prepped folder. Default: <code>0.Prepped</code>.</li>
              <li>Add captions for the prepped files. Captions must start with <code>&lt;trigger&gt;,</code> exactly.</li>
              <li>Run <b>Validate Everything</b>.</li>
            </ol>
            <p><b>Caption Settings</b> controls manual/template captions, local model settings, API model settings, and custom command captions. API modes may send images to the selected provider; manual/template mode does not.</p>

            <h2>Library</h2>
            {guide_img("library.png", "Library: project list, manifest preview, cached prepped thumbnails, and large preview.")}
            <p>The Library scans the app-managed <code>datasets\\</code> folder and any custom project roots in Settings. It de-dupes folders, shows project counts, previews the manifest, and shows cached thumbnails from the configured prepped folder. The thumbnail cache is shared app-wide in <code>thumbnail_cache\\</code>, so the app is not making a pile of duplicate little images.</p>

            <h2>Ostris Configs / AI Toolkit Presets</h2>
            {guide_img("ostris.png", "Ostris config builder: form controls and editable YAML side by side.")}
            <p>This tab recreates the important shape of the Ostris new-job GUI inside PrepMI-PrepYU. The left side is form controls; the right side is raw YAML. Form edits update YAML. YAML edits update the form when parsing works. If parsing fails, the app shows the error and does not stomp your text.</p>
            <p>Use <b>New From Dataset</b> to start from the selected project. Then set architecture/model path, dataset folder, caption extension, rank/alpha, optimizer/training values, sample prompts, and resolution. Export the YAML, then load/run it manually in Ostris AI Toolkit.</p>
            <p>The sample prompt section has add/remove/reorder-style controls, trigger insertion, import/export, and trigger validation. If your sample prompts use the wrong trigger, the app should complain before you waste time.</p>

            <h2>Settings</h2>
            <p>Settings has project roots, caption model locations, provider API keys, theme presets, and the separate progress-bar gradient. The main UI accent color is its own thing. The progress gradient is also its own thing. If the gradient is off, progress bars use the current accent color.</p>

            <h2>Key Binds And Mouse Moves</h2>
            <table>
              <tr><th>Action</th><th>What it does</th></tr>
              <tr><td>Drag folder onto Dataset Prep</td><td>Open/import a project folder.</td></tr>
              <tr><td>Drag images onto image grids</td><td>Load images into the active review/split list.</td></tr>
              <tr><td>Manual crop: left-drag empty preview</td><td>Create the one crop box for that image.</td></tr>
              <tr><td>Manual crop: left-drag inside box</td><td>Move the existing crop box.</td></tr>
              <tr><td>Manual crop: right-click inside box</td><td>Remove the crop box.</td></tr>
              <tr><td>Image lists/grids: Ctrl+A, Shift-click, Ctrl-click</td><td>Use the normal Windows Explorer selection moves: select all, select a range, or add/remove individual images from the selection.</td></tr>
              <tr><td>Mouse wheel over text fields/dropdowns/spinners</td><td>Does not change values. This is intentional, because accidental scroll edits are terrible.</td></tr>
              <tr><td>Ctrl+A in text editors</td><td>Select text normally.</td></tr>
              <tr><td>Standard text shortcuts</td><td>Copy/paste/undo/redo work where Qt text fields support them.</td></tr>
            </table>

            <h2>Suggested Workflow</h2>
            <ol>
              <li>Create or drop/import a project.</li>
              <li>Put raw sheets/source images in the configured project image folder.</li>
              <li>Use Cut / Split if sheets, faces, or manual crops need cleanup.</li>
              <li>Use Cut / Split export to fill the prepped folder.</li>
              <li>Review and caption the prepped images in Dataset Prep with a real trigger token. No surprise trigger magic.</li>
              <li>Validate everything.</li>
              <li>Build/tweak Ostris YAML and run it manually in AI Toolkit.</li>
            </ol>
            <p>That is the loop. The app is here to keep the boring folder bookkeeping honest while you make the actual taste calls.</p>
            """
        text.setHtml(guide_html)
        self.guide_html = guide_html
        self.guide_browser = text
        return text

    def open_guide_image(self, url) -> None:
        value = url.toString()
        path = Path(url.toLocalFile()) if url.isLocalFile() else Path(value)
        try:
            is_guide_image = path.resolve().is_relative_to(GUIDE_ASSET_DIR.resolve())
        except AttributeError:
            is_guide_image = str(path.resolve()).casefold().startswith(str(GUIDE_ASSET_DIR.resolve()).casefold())
        if not is_guide_image:
            return
        if not path.exists():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(path.name)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, False)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        scroll = ClickCloseScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(False)
        scroll.setCursor(Qt.PointingHandCursor)
        scroll.clicked.connect(dialog.accept)
        scroll.viewport().setCursor(Qt.PointingHandCursor)
        label = ClickCloseLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setCursor(Qt.PointingHandCursor)
        pixmap = QPixmap(str(path))
        label.setPixmap(pixmap)
        label.resize(pixmap.size())
        label.clicked.connect(dialog.accept)
        scroll.setWidget(label)
        layout.addWidget(scroll, 1)
        screen = dialog.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else self.geometry()
        width = min(pixmap.width(), available.width())
        height = min(pixmap.height(), available.height())
        dialog.resize(width, height)
        dialog.move(available.x() + (available.width() - width) // 2, available.y() + (available.height() - height) // 2)
        dialog.exec()

    def open_guide(self) -> None:
        if hasattr(self, "tabs"):
            for index in range(self.tabs.count()):
                if self.tabs.tabText(index) == "Guide":
                    self.tabs.setCurrentIndex(index)
                    return

    def build_ostris_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        for text, slot, tip in [
            ("New From Project", self.new_ostris_yaml, "Create YAML from current project/export settings."),
            ("Import YAML", self.import_yaml, "Load an existing .yaml/.yml config."),
            ("Validate YAML", self.validate_yaml, "Parse YAML and check common fields."),
            ("Export YAML", self.export_yaml, "Save the visible YAML text to a file."),
            ("Scan Toolkit Examples", self.scan_toolkit_examples, "Import presets from Settings -> Ostris Toolkit Path."),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            top.addWidget(add_help(button, tip))
        top.addStretch(1)
        layout.addLayout(top)
        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setSpacing(12)
        cards = QVBoxLayout()
        cards.setSpacing(12)
        form_layout.addLayout(cards)

        self.job_name = QLineEdit("dataset_lora")
        self.gpu_id = QLineEdit("0")
        self.config_trigger = QLineEdit(self.trigger_edit.text() if hasattr(self, "trigger_edit") else "")
        self.job_type = QComboBox()
        self.job_type.addItem("LoRA Trainer", "diffusion_trainer")
        self.job_type.addItem("Concept Slider", "concept_slider")

        self.model_arch = QComboBox()
        for arch in ostris_model_arch_registry():
            self.model_arch.addItem(f"{arch['label']}  [{arch['arch']}]", arch["arch"])
        self.model_name_or_path = QLineEdit("")
        self.training_adapter_path = QLineEdit("")
        self.extras_name_or_path = QLineEdit("")
        self.low_vram = QCheckBox("Low VRAM")
        self.layer_offloading = QCheckBox("Layer Offloading")
        self.match_target_res = QCheckBox("Match Target Res")
        self.kv_cache = QCheckBox("KV Cache")

        self.quantize_transformer = QComboBox()
        self.quantize_text_encoder = QComboBox()
        for combo in [self.quantize_transformer, self.quantize_text_encoder]:
            for value, label in [
                ("", "- NONE -"),
                ("qfloat8", "qfloat8 (default)"),
                ("float8", "float8"),
                ("convrot8", "8bit convrot"),
                ("convrot4", "4bit convrot (nvfp4)"),
                ("convrotint4", "4bit convrot"),
                ("uint4", "4 bit"),
                ("uint3", "3 bit"),
                ("uint2", "2 bit"),
            ]:
                combo.addItem(label, value)
        self.compile_model = QCheckBox("Compile Model")

        self.network_type = QComboBox()
        self.network_type.addItem("LoRA", "lora")
        self.network_type.addItem("LoKr", "lokr")
        self.lokr_factor = QComboBox()
        for value, label in [("-1", "Auto"), ("4", "4"), ("8", "8"), ("16", "16"), ("32", "32")]:
            self.lokr_factor.addItem(label, value)
        self.rank = QSpinBox()
        self.rank.setRange(1, 512)
        self.rank.setValue(32)
        self.alpha = QSpinBox()
        self.alpha.setRange(1, 512)
        self.alpha.setValue(32)
        self.conv_rank = QSpinBox()
        self.conv_rank.setRange(0, 512)
        self.conv_rank.setValue(16)

        self.dtype = QComboBox()
        self.dtype.addItems(["bf16", "fp16", "fp32"])
        self.save_every = QSpinBox()
        self.save_every.setRange(1, 100000)
        self.save_every.setValue(250)
        self.max_checkpoints = QSpinBox()
        self.max_checkpoints.setRange(1, 1000)
        self.max_checkpoints.setValue(4)

        self.train_folder = QLineEdit("output")
        self.device = QComboBox()
        self.device.addItems(["cuda", "cuda:0", "cpu", "mps"])
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 128)
        self.batch_size.setValue(1)
        self.gradient_accumulation = QSpinBox()
        self.gradient_accumulation.setRange(1, 128)
        self.gradient_accumulation.setValue(1)
        self.steps = QSpinBox()
        self.steps.setRange(1, 1000000)
        self.steps.setValue(3000)
        self.optimizer = QLineEdit("adamw8bit")
        self.lr = QLineEdit("0.0001")
        self.weight_decay = QLineEdit("0.0001")
        self.timestep_type = QComboBox()
        self.timestep_type.addItems(["sigmoid", "weighted", "linear", "logit_normal"])
        self.loss_type = QComboBox()
        self.loss_type.addItems(["mse", "mae", "huber"])
        self.unload_te = QCheckBox("Unload TE")
        self.cache_text_embeddings = QCheckBox("Cache Text Embeddings")
        self.gradient_checkpointing = QCheckBox("Gradient Checkpointing")
        self.gradient_checkpointing.setChecked(True)

        self.dataset_folder = QLineEdit("")
        self.caption_extension = QComboBox()
        self.caption_extension.addItems(["txt", ".txt", "caption", "text"])
        self.caption_extension.setCurrentText("txt")
        self.caption_dropout = QLineEdit("0.05")
        self.num_repeats = QSpinBox()
        self.num_repeats.setRange(1, 1000)
        self.num_repeats.setValue(1)
        self.network_weight = QLineEdit("1")
        self.cache_latents = QCheckBox("Cache Latents")
        self.is_regularization = QCheckBox("Is Regularization")
        self.resolution = QLineEdit("512, 768, 1024")

        self.sample_every = QSpinBox()
        self.sample_every.setRange(1, 100000)
        self.sample_every.setValue(250)
        self.sample_start_step = QSpinBox()
        self.sample_start_step.setRange(0, 100000)
        self.sample_start_step.setValue(0)
        self.sample_sampler = QComboBox()
        self.sample_sampler.addItems(["flowmatch", "ddpm", "euler", "lms"])
        self.guidance_scale = QLineEdit("1")
        self.sample_steps = QSpinBox()
        self.sample_steps.setRange(1, 200)
        self.sample_steps.setValue(9)
        self.sample_width = QSpinBox()
        self.sample_width.setRange(64, 4096)
        self.sample_width.setValue(1024)
        self.sample_height = QSpinBox()
        self.sample_height.setRange(64, 4096)
        self.sample_height.setValue(1024)
        self.sample_seed = QSpinBox()
        self.sample_seed.setRange(0, 2147483647)
        self.sample_seed.setValue(42)
        self.walk_seed = QCheckBox("Walk Seed")
        self.force_first_sample = QCheckBox("Force First Sample")
        self.disable_sampling = QCheckBox("Disable Sampling")
        self.slider_target_class = QLineEdit("person")
        self.slider_positive_prompt = QLineEdit("person who is happy")
        self.slider_negative_prompt = QLineEdit("person who is sad")
        self.slider_anchor_class = QLineEdit("")

        def card(title: str, rows: list[tuple[str, QWidget, str]], min_height: int = 0) -> QGroupBox:
            box = QGroupBox(title)
            if min_height:
                box.setMinimumHeight(min_height)
            form = QFormLayout(box)
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            form.setVerticalSpacing(8)
            for label, widget, tip in rows:
                form.addRow(label, add_help(widget, tip))
            return box

        cards.addWidget(card("Job", [
            ("Training Name", self.job_name, "Ostris config.name and output folder/file name."),
            ("GPU ID", self.gpu_id, "UI GPU selector equivalent; exported device still lives in process.device."),
            ("Trigger Word", self.config_trigger, "Ostris trigger_word. Sample prompts must include this manually."),
            ("Job Type", self.job_type, "Ostris process type: diffusion_trainer for LoRA Trainer, concept_slider for Concept Slider."),
        ], 190))
        cards.addWidget(card("Model", [
            ("Model Architecture", self.model_arch, "Ostris model.arch value with the same UI label."),
            ("Name or Path", self.model_name_or_path, "Ostris model.name_or_path. Accepts Hugging Face IDs or local paths exactly like AI Toolkit."),
            ("Training Adapter Path", self.training_adapter_path, "Ostris model.assistant_lora_path. Shown for adapter-based architectures such as Z-Image Turbo."),
            ("Extras Name or Path", self.extras_name_or_path, "Ostris model.extras_name_or_path for architectures that need an extra base path."),
            ("Options", self.low_vram, "Ostris Low VRAM option."),
            ("Layer Offloading", self.layer_offloading, "Ostris experimental layer offloading option where supported."),
            ("Match Target Res", self.match_target_res, "Ostris model.model_kwargs.match_target_res for supported edit/instruction architectures."),
            ("KV Cache", self.kv_cache, "Ostris model.model_kwargs.kv_cache for supported architectures."),
        ], 300))
        cards.addWidget(card("Quantize / Compile", [
            ("Transformer", self.quantize_transformer, "Ostris transformer quantization selector. Blank means quantize false."),
            ("Text Encoder", self.quantize_text_encoder, "Ostris text encoder quantization selector. Blank means quantize_te false."),
            ("Compile Options", self.compile_model, "Ostris Compile Model option."),
        ], 160))
        self.target_card = card("Target", [
            ("Target Type", self.network_type, "Ostris network.type."),
            ("LoKr Factor", self.lokr_factor, "Ostris network.lokr_factor for LoKr targets."),
            ("Linear Rank", self.rank, "Ostris network.linear."),
            ("LoRA Alpha", self.alpha, "Ostris network.linear_alpha."),
            ("Conv Rank", self.conv_rank, "Ostris network.conv. Some architectures disable or ignore this."),
        ], 230)
        cards.addWidget(self.target_card)
        self.slider_card = card("Slider", [
            ("Target Class", self.slider_target_class, "Ostris slider.target_class for Concept Slider jobs."),
            ("Positive Prompt", self.slider_positive_prompt, "Ostris slider.positive_prompt."),
            ("Negative Prompt", self.slider_negative_prompt, "Ostris slider.negative_prompt."),
            ("Anchor Class", self.slider_anchor_class, "Ostris slider.anchor_class."),
        ], 230)
        cards.addWidget(self.slider_card)
        cards.addWidget(card("Save", [
            ("Data Type", self.dtype, "Ostris save dtype and train dtype."),
            ("Save Every", self.save_every, "Ostris save.save_every."),
            ("Max Step Saves to Keep", self.max_checkpoints, "Ostris save.max_step_saves_to_keep."),
        ], 160))
        cards.addWidget(card("Training", [
            ("Training Folder", self.train_folder, "Ostris process.training_folder."),
            ("Device", self.device, "Ostris process.device."),
            ("Batch Size", self.batch_size, "Ostris train.batch_size."),
            ("Gradient Accumulation", self.gradient_accumulation, "Ostris train.gradient_accumulation."),
            ("Steps", self.steps, "Ostris train.steps."),
            ("Optimizer", self.optimizer, "Ostris train.optimizer."),
            ("Learning Rate", self.lr, "Ostris train.lr."),
            ("Weight Decay", self.weight_decay, "Ostris train.optimizer_params.weight_decay."),
            ("Timestep Type", self.timestep_type, "Ostris train.timestep_type."),
            ("Loss Type", self.loss_type, "Ostris train.loss_type."),
            ("Unload TE", self.unload_te, "Ostris train.unload_text_encoder."),
            ("Cache Text Embeddings", self.cache_text_embeddings, "Ostris train.cache_text_embeddings."),
            ("Gradient Checkpointing", self.gradient_checkpointing, "Ostris train.gradient_checkpointing."),
        ], 430))
        cards.addWidget(card("Dataset 1", [
            ("Target Dataset", self.dataset_folder, "Ostris datasets[0].folder_path."),
            ("Caption Extension", self.caption_extension, "Ostris datasets[0].caption_ext. AI Toolkit examples use txt without a leading dot."),
            ("Caption Dropout Rate", self.caption_dropout, "Ostris datasets[0].caption_dropout_rate."),
            ("Num Repeats", self.num_repeats, "Ostris datasets[0].num_repeats."),
            ("LoRA Weight", self.network_weight, "Ostris datasets[0].network_weight."),
            ("Resolutions", self.resolution, "Ostris datasets[0].resolution list, usually 512, 768, 1024."),
            ("Cache Latents", self.cache_latents, "Ostris datasets[0].cache_latents_to_disk."),
            ("Is Regularization", self.is_regularization, "Ostris datasets[0].is_reg."),
        ], 310))
        cards.addWidget(card("Sample", [
            ("Sample Every", self.sample_every, "Ostris sample.sample_every."),
            ("Sample Start Step", self.sample_start_step, "Ostris sample.sample_start_step."),
            ("Sampler", self.sample_sampler, "Ostris sample.sampler."),
            ("Guidance Scale", self.guidance_scale, "Ostris sample.guidance_scale."),
            ("Sample Steps", self.sample_steps, "Ostris sample.sample_steps."),
            ("Width", self.sample_width, "Ostris sample.width."),
            ("Height", self.sample_height, "Ostris sample.height."),
            ("Seed", self.sample_seed, "Ostris sample.seed."),
            ("Walk Seed", self.walk_seed, "Ostris sample.walk_seed."),
            ("Force First Sample", self.force_first_sample, "Ostris train.force_first_sample."),
            ("Disable Sampling", self.disable_sampling, "Ostris train.disable_sampling."),
        ], 380))

        sample_box = QGroupBox("Sample Prompts")
        sample_layout = QVBoxLayout(sample_box)
        self.sample_rows: list[dict[str, QWidget]] = []
        sample_actions = QHBoxLayout()
        for text, slot, tip in [
            ("Add Prompt", self.add_blank_sample_prompt, "Add a new Ostris-style sample prompt row."),
            ("Insert Trigger", self.insert_trigger_in_samples, "Append trigger token to sample editor."),
            ("Starter From Captions", self.samples_from_captions, "Generate starter prompts from current captions."),
            ("Import Text", self.import_samples, "Import prompts from a .txt file."),
            ("Export Text", self.export_samples, "Export prompts to a .txt file."),
            ("Validate Trigger", self.validate_sample_triggers, "Warn when sample prompts miss or mismatch the trigger."),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            sample_actions.addWidget(add_help(button, tip))
        sample_layout.addLayout(sample_actions)
        self.sample_rows_widget = QWidget()
        self.sample_rows_layout = QVBoxLayout(self.sample_rows_widget)
        self.sample_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_rows_layout.setSpacing(8)
        sample_layout.addWidget(self.sample_rows_widget)
        self.add_sample_prompt_row({"prompt": ""})
        form_layout.addWidget(sample_box)
        form_layout.addStretch(1)
        form_widget.setMinimumWidth(760)
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(form_widget)
        form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        form_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        split.addWidget(form_scroll)
        yaml_widget = QWidget()
        yaml_layout = QVBoxLayout(yaml_widget)
        self.yaml_status = QLabel("YAML is editable. Parsing errors are shown here without overwriting your text.")
        yaml_layout.addWidget(self.yaml_status)
        self.yaml_editor = QPlainTextEdit()
        self.yaml_editor.textChanged.connect(self.yaml_text_changed)
        yaml_layout.addWidget(self.yaml_editor, 1)
        split.addWidget(yaml_widget)
        split.setSizes([760, 640])
        for widget in [
            self.job_name, self.gpu_id, self.config_trigger, self.job_type, self.model_arch, self.model_name_or_path,
            self.training_adapter_path, self.extras_name_or_path, self.low_vram, self.layer_offloading,
            self.match_target_res, self.kv_cache, self.quantize_transformer, self.quantize_text_encoder,
            self.compile_model, self.network_type, self.lokr_factor, self.rank, self.alpha, self.conv_rank,
            self.dtype, self.save_every, self.max_checkpoints, self.train_folder, self.device, self.batch_size,
            self.gradient_accumulation, self.steps, self.optimizer, self.lr, self.weight_decay, self.timestep_type,
            self.loss_type, self.unload_te, self.cache_text_embeddings, self.gradient_checkpointing,
            self.slider_target_class, self.slider_positive_prompt, self.slider_negative_prompt, self.slider_anchor_class,
            self.dataset_folder, self.caption_extension, self.caption_dropout, self.num_repeats, self.network_weight,
            self.cache_latents, self.is_regularization, self.resolution, self.sample_every, self.sample_start_step,
            self.sample_sampler, self.guidance_scale, self.sample_steps, self.sample_width, self.sample_height,
            self.sample_seed, self.walk_seed, self.force_first_sample, self.disable_sampling
        ]:
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self.form_to_yaml)
            elif hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self.form_to_yaml)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.form_to_yaml)
            elif hasattr(widget, "stateChanged"):
                widget.stateChanged.connect(self.form_to_yaml)
        self.model_arch.currentIndexChanged.connect(self.apply_ostris_arch_defaults)
        self.job_type.currentIndexChanged.connect(self.update_ostris_job_type_layout)
        self.apply_ostris_arch_defaults()
        self.update_ostris_job_type_layout()
        self.new_ostris_yaml()
        return tab

    def refresh_dataset_paths(self) -> None:
        text = self.dataset_root_edit.text().strip() if hasattr(self, "dataset_root_edit") else ""
        if not text:
            self.dataset_root = None
            self.manifest = EmptyManifest()
            return
        self.dataset_root = Path(text)
        self.manifest = Manifest(self.dataset_root)
        self.ensure_dataset_structure(save=False)
        if hasattr(self, "anchor_combo"):
            self.refresh_anchors()

    def dataset_root_edited(self) -> None:
        text = self.dataset_root_edit.text().strip()
        if not text:
            self.dataset_root = None
            self.manifest = EmptyManifest()
            self.dataset_list.show_empty()
            self.update_split_project_label()
            return
        root = Path(text)
        if not root.exists():
            self.status.setText(f"Project path does not exist yet: {root}")
            return
        self.open_project_root(root, save_last=True)

    def known_project_roots(self) -> list[Path]:
        hidden = {normalized_path_key(Path(path)) for path in self.settings.get("hidden_datasets", [])}
        roots = self.project_library_roots()
        found: list[Path] = []
        seen: set[str] = set()
        for base in roots:
            if not base.exists():
                continue
            for root in self.project_roots_in(base):
                key = normalized_path_key(root)
                if key in hidden or key in seen:
                    continue
                found.append(root)
                seen.add(key)
        return sorted(found, key=self.project_modified_time, reverse=True)

    def project_library_roots(self) -> list[Path]:
        roots = [DEFAULT_DATASETS_DIR]
        roots.extend(Path(path) for path in self.settings.get("custom_dataset_roots", []))
        unique: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = normalized_path_key(root)
            if key not in seen:
                unique.append(root)
                seen.add(key)
        return unique

    def is_inside_path(self, child: Path, parent: Path) -> bool:
        try:
            child.resolve().relative_to(parent.resolve())
            return child.resolve() != parent.resolve()
        except Exception:
            return False

    def can_delete_project_folder(self, root: Path) -> tuple[bool, str]:
        if not root.exists() or not root.is_dir():
            return False, "The selected path is not an existing folder."
        for library_root in self.project_library_roots():
            if library_root.exists() and self.is_inside_path(root, library_root):
                return True, ""
        allowed = "\n".join(str(path) for path in self.project_library_roots())
        return False, (
            "For safety, PrepMI-PrepYU only deletes project folders inside configured project roots.\n\n"
            f"Selected folder:\n{root.resolve()}\n\n"
            f"Configured project roots:\n{allowed or 'none'}\n\n"
            "Use Archive/Hide or remove the folder manually if this is outside the app-managed project roots."
        )

    def ensure_project_manifest_file(self, root: Path) -> None:
        try:
            Manifest(root)
        except Exception as exc:
            self.status.setText(f"Could not create manifest for {root}: {exc}")

    def project_roots_in(self, base: Path) -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def add_candidate(path: Path, create_manifest: bool = False) -> None:
            key = normalized_path_key(path)
            if key not in seen:
                if create_manifest:
                    self.ensure_project_manifest_file(path)
                candidates.append(path)
                seen.add(key)

        if (base / "manifest.json").exists():
            add_candidate(base)
        try:
            for child in base.iterdir():
                if child.is_dir():
                    add_candidate(child, create_manifest=True)
        except OSError:
            return candidates
        for manifest_path in base.rglob("manifest.json"):
            add_candidate(manifest_path.parent)
        return candidates

    def project_modified_time(self, root: Path) -> float:
        manifest_path = root / "manifest.json"
        try:
            if manifest_path.exists():
                return manifest_path.stat().st_mtime
            return root.stat().st_mtime
        except OSError:
            return 0.0

    def refresh_project_combo(self) -> None:
        if not hasattr(self, "project_combo"):
            return
        current = self.dataset_root_edit.text().strip() if hasattr(self, "dataset_root_edit") else ""
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("Available projects...", "")
        selected_index = 0
        for root in self.known_project_roots():
            label = f"{root.name}  |  {root}"
            self.project_combo.addItem(label, str(root))
            if current and str(root) == current:
                selected_index = self.project_combo.count() - 1
        self.project_combo.setCurrentIndex(selected_index)
        self.project_combo.blockSignals(False)

    def project_combo_changed(self, index: int) -> None:
        if index <= 0:
            return
        path = self.project_combo.itemData(index)
        if not path:
            return
        self.dataset_root_edit.setText(str(path))
        self.dataset_root_edited()

    def require_dataset_root(self) -> Path | None:
        text = self.dataset_root_edit.text().strip() if hasattr(self, "dataset_root_edit") else ""
        if text:
            self.dataset_root = Path(text)
            return self.dataset_root
        QMessageBox.information(self, APP_NAME, "Create or select a project first.")
        return None

    def ensure_dataset_structure(self, save: bool = True) -> None:
        if self.dataset_root is None:
            text = self.dataset_root_edit.text().strip() if hasattr(self, "dataset_root_edit") else ""
            if text:
                self.dataset_root = Path(text)
            else:
                name, ok = QInputDialog.getText(self, "Create Project", "Project name:")
                if not ok or not name.strip():
                    return
                safe_name = "".join(char for char in name.strip() if char not in '<>:"/\\|?*').strip()
                if not safe_name:
                    QMessageBox.warning(self, APP_NAME, "Project name contains no valid folder characters.")
                    return
                self.dataset_root = DEFAULT_DATASETS_DIR / safe_name
                self.dataset_root_edit.setText(str(self.dataset_root))
            self.manifest = Manifest(self.dataset_root)
        for rel in dict.fromkeys(self.folder_preferences().values()):
            (self.dataset_root / rel).mkdir(parents=True, exist_ok=True)
        export = self.manifest.data.setdefault("export", {})
        if not self.manifest.data.get("dataset", {}).get("last_exported"):
            export["folder"] = str(self.project_folder("export"))
        if save:
            self.settings["last_dataset_root"] = str(self.dataset_root)
            save_settings(self.settings)
            self.manifest.data.setdefault("preferences", {})["folder_structure"] = self.folder_preferences()
            self.manifest.save("project structure ensured")
            self.status.setText(f"Project structure ready: {self.dataset_root}")

    def handle_project_folder_drop(self, folder: Path) -> None:
        folder = folder.resolve()
        app_root = DEFAULT_DATASETS_DIR.resolve()
        try:
            in_app_projects = folder == app_root or folder.is_relative_to(app_root)
        except AttributeError:
            in_app_projects = str(folder).casefold().startswith(str(app_root).casefold())
        if in_app_projects:
            target = folder
        else:
            target = unique_path(DEFAULT_DATASETS_DIR / folder.name)
            self.begin_progress("Importing dropped project", 1)
            try:
                shutil.copytree(folder, target)
            except Exception as exc:
                self.end_progress("Project import failed")
                QMessageBox.warning(self, APP_NAME, f"Could not import project folder:\n\n{folder}\n\n{exc}")
                return
            self.update_progress(1, f"Imported dropped project: {target.name}")
            self.end_progress(f"Imported dropped project: {target}")
            self.normalize_imported_project(target)
        self.open_project_root(target, save_last=True)

    def normalize_imported_project(self, root: Path) -> None:
        dataset_dir = self.project_folder("project_images", root)
        dataset_images = image_paths_from_items([dataset_dir])
        root_images = image_paths_from_items([root])
        if dataset_images or not root_images:
            return
        dataset_dir.mkdir(parents=True, exist_ok=True)
        for path in root_images:
            try:
                shutil.copy2(path, unique_path(dataset_dir / path.name))
            except Exception:
                continue

    def handle_dataset_drop(self, paths: list[Path]) -> None:
        if len(paths) == 1 and paths[0].is_dir():
            self.handle_project_folder_drop(paths[0])
            return
        self.load_dataset_images_from_paths(paths)

    def open_project_root(self, root: Path, save_last: bool = True) -> None:
        self.dataset_root = root
        self.dataset_root_edit.setText(str(root))
        self.manifest = Manifest(root)
        self.ensure_dataset_structure(save=save_last)
        self.refresh_project_thumbnail_cache(root)
        self.load_current_dataset_images()
        self.update_split_project_label()
        self.refresh_library()
        self.refresh_project_combo()
        self.scan_project_sheets()
        self.status.setText(f"Loaded project: {root}")

    def refresh_project_thumbnail_cache(self, root: Path) -> None:
        if not root.exists():
            return
        images = image_paths_from_items([root], recursive=True)
        index = load_thumbnail_index()
        current_keys = {normalized_path_key(path) for path in images}

        removed_keys: list[str] = []
        for key, entry in list(index.items()):
            source = Path(entry.get("source", ""))
            try:
                source.resolve().relative_to(root.resolve())
                belongs_to_project = True
            except Exception:
                belongs_to_project = False
            if not belongs_to_project:
                continue
            signature_changed = False
            if source.exists():
                try:
                    sig = thumbnail_signature(source)
                    signature_changed = sig.get("mtime_ns") != entry.get("mtime_ns") or sig.get("size") != entry.get("size")
                except Exception:
                    signature_changed = True
            if key not in current_keys or not source.exists() or signature_changed:
                thumb = Path(entry.get("thumb", ""))
                try:
                    if thumb.exists():
                        thumb.unlink()
                except Exception:
                    pass
                removed_keys.append(key)
                index.pop(key, None)
        if removed_keys:
            save_thumbnail_index(index)

        if images:
            self.begin_progress("Updating project thumbnails", len(images))
        made = 0
        for index_num, path in enumerate(images, start=1):
            if cached_thumbnail_path(path):
                made += 1
            self.update_progress(index_num, f"Updating thumbnail: {path.name}")
        if images:
            self.end_progress(f"Thumbnail cache ready: {made} image(s)")

    def rename_dataset(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        if not root.exists():
            QMessageBox.warning(self, APP_NAME, "The selected project folder does not exist yet.")
            return
        new_name, ok = QInputDialog.getText(self, "Rename Project", "New project name:", text=root.name)
        if not ok or not new_name.strip() or new_name.strip() == root.name:
            return
        safe_name = "".join(char for char in new_name.strip() if char not in '<>:"/\\|?*').strip()
        if not safe_name:
            QMessageBox.warning(self, APP_NAME, "Project name contains no valid folder characters.")
            return
        new_root = root.with_name(safe_name)
        if new_root.exists():
            QMessageBox.warning(self, APP_NAME, f"A project named '{safe_name}' already exists.")
            return
        root.rename(new_root)
        self.dataset_root = new_root
        self.dataset_root_edit.setText(str(new_root))
        self.manifest = Manifest(new_root)
        self.manifest.data["dataset"]["name"] = safe_name
        self.manifest.data["dataset"]["root"] = str(new_root)
        export = self.manifest.data.get("export", {})
        if export.get("folder"):
            export["folder"] = str(self.project_folder("export", new_root))
        self.manifest.save(f"project renamed from {root.name} to {safe_name}")
        self.settings["last_dataset_root"] = str(new_root)
        save_settings(self.settings)
        self.refresh_library()
        self.refresh_project_combo()
        self.update_split_project_label()
        self.scan_project_sheets()
        self.status.setText(f"Renamed project to {safe_name}")

    def delete_dataset(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        if not root.exists():
            QMessageBox.warning(self, APP_NAME, "The selected project folder does not exist.")
            return
        allowed, reason = self.can_delete_project_folder(root)
        if not allowed:
            QMessageBox.warning(self, APP_NAME, reason)
            return
        reply = QMessageBox.warning(
            self,
            "Delete Project",
            f"Delete this project folder and all contents?\n\n{root.resolve()}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        confirm, ok = QInputDialog.getText(self, "Confirm Delete", f"Type DELETE to permanently delete:\n{root.resolve()}")
        if not ok or confirm != "DELETE":
            return
        shutil.rmtree(root)
        self.dataset_root = None
        self.manifest = EmptyManifest()
        self.dataset_root_edit.clear()
        self.dataset_list.show_empty()
        self.split_inputs = []
        self.refresh_split_list()
        self.update_split_project_label()
        self.caption_editor.clear()
        self.reason_tags.clear()
        self.settings.pop("last_dataset_root", None)
        save_settings(self.settings)
        self.refresh_library()
        self.refresh_project_combo()
        self.status.setText("Project deleted")

    def load_split_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Load image sheets", str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)")
        self.add_split_paths([Path(f) for f in files])

    def load_split_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Load image sheet folder", str(Path.home()))
        if folder:
            self.add_split_paths([Path(folder)])

    def add_split_paths(self, paths: list[Path]) -> None:
        found = image_paths_from_items(paths)
        existing = {p.resolve() for p in self.split_inputs if p.exists()}
        for path in found:
            if path.resolve() not in existing:
                self.split_inputs.append(path)
        self.refresh_split_list()
        if self.split_inputs and not self.split_output.text():
            if self.dataset_root and self.project_images_folder(quiet=True) in self.split_inputs[0].parents:
                self.split_output.setText(str(self.project_folder("split")))
            else:
                self.split_output.setText(str(self.split_inputs[0].parent / Path(self.folder_rel("split")).name))
        self.status.setText(f"Loaded {len(found)} split source image(s)")

    def refresh_split_list(self) -> None:
        self.split_list.clear()
        if not self.split_inputs:
            self.split_list.show_empty()
            return
        for path in self.split_inputs:
            self.split_list.addItem(sheet_grid_item(path))
        self.split_list.setCurrentRow(0)

    def update_split_project_label(self) -> None:
        if hasattr(self, "split_project_label"):
            self.split_project_label.setText(f"Project: {self.dataset_root}" if self.dataset_root else "Project: none")

    def project_images_folder(self, quiet: bool = False) -> Path | None:
        root = self.dataset_root if quiet else self.require_dataset_root()
        if root is None:
            return None
        return self.project_folder("project_images", root)

    def load_project_images_for_split(self) -> None:
        folder = self.project_images_folder()
        if folder is None:
            return
        self.add_split_paths([folder])
        self.split_output.setText(str(self.project_folder("split")))

    def is_likely_sheet(self, path: Path) -> bool:
        try:
            with Image.open(path) as image:
                width, height = image.size
                rows, cols = detect_grid(width, height)
        except Exception:
            return False
        if rows * cols <= 1:
            return False
        cell_w = width / max(1, cols)
        cell_h = height / max(1, rows)
        if min(cell_w, cell_h) < 96:
            return False
        aspect = width / max(1, height)
        return rows * cols >= 3 or aspect >= 1.75 or aspect <= 0.58

    def scan_project_sheets(self) -> None:
        folder = self.project_images_folder(quiet=True)
        if folder is None:
            return
        images = image_paths_from_items([folder])
        sheets: list[Path] = []
        if images:
            self.begin_progress("Scanning project sheets", len(images))
        for index, path in enumerate(images, start=1):
            if self.is_likely_sheet(path):
                sheets.append(path)
            self.update_progress(index, f"Scanning project sheets: {path.name}")
        self.split_inputs = []
        self.add_split_paths(sheets)
        self.split_output.setText(str(self.project_folder("split")))
        self.split_log.setPlainText(f"Scanned {len(images)} image(s) in {folder}\nQueued {len(sheets)} likely sheet(s).")
        if images:
            self.end_progress(f"Queued {len(sheets)} likely sheet(s) from project")
        else:
            self.status.setText("No project images found to scan")

    def split_selection_changed(self, current: QListWidgetItem | None) -> None:
        path = Path(current.data(Qt.UserRole)) if current and current.data(Qt.UserRole) else None
        self.split_current = path
        if path:
            if not self.split_output.text():
                self.split_output.setText(str(path.parent / Path(self.folder_rel("split")).name))
            self.split_preview.set_image(path)
            self.refresh_manual_crop_list()
            self.preview_split_cuts()

    def split_path_key(self, path: Path | None = None) -> str:
        target = path or self.split_current
        return normalized_path_key(target) if target else ""

    def current_mode_boxes(self, path: Path | None = None) -> list[tuple[int, int, int, int]]:
        key = self.split_path_key(path)
        if self.cut_mode.currentText() == "Face crops":
            return self.split_face_crops.get(key, [])
        if self.cut_mode.currentText() == "Manual crops":
            return self.split_manual_crops.get(key, [])
        return []

    def crop_ratio_value(self) -> float | None:
        if not hasattr(self, "crop_ratio"):
            return 1.0
        text = self.crop_ratio.currentText()
        if text == "Free":
            return None
        left, right = text.split(":", 1)
        return max(0.01, float(left) / max(0.01, float(right)))

    def crop_ratio_changed(self, _text: str = "") -> None:
        if hasattr(self, "split_preview"):
            self.split_preview.set_crop_aspect_ratio(self.crop_ratio_value())
        if hasattr(self, "cut_mode") and self.cut_mode.currentText() == "Face crops":
            self.split_face_crops.clear()
            self.preview_split_cuts()

    def cut_mode_changed(self, mode: str) -> None:
        grid_visible = mode == "Grid / Sheet"
        face_visible = mode == "Face crops"
        manual_visible = mode == "Manual crops"

        def set_field_visible(widget: QWidget, visible: bool) -> None:
            widget.setVisible(visible)
            label = self.cut_controls_form.labelForField(widget) if hasattr(self, "cut_controls_form") else None
            if label:
                label.setVisible(visible)

        for widget in [self.split_rows, self.split_cols, self.crop_left, self.crop_top, self.crop_right, self.crop_bottom, self.auto_detect]:
            set_field_visible(widget, grid_visible)
        for widget in [self.face_detector, self.face_framing, self.face_padding, self.face_min_size, self.face_confidence, self.face_actions_row]:
            set_field_visible(widget, face_visible)
        for widget in [self.manual_crop_list, self.manual_actions_row]:
            set_field_visible(widget, manual_visible)
        set_field_visible(self.crop_ratio, face_visible or manual_visible)
        self.crop_ratio_changed()
        self.split_preview.set_crop_drawing_enabled(manual_visible)
        self.split_preview.set_box_editing_enabled(face_visible or manual_visible)
        self.refresh_manual_crop_list()
        self.preview_split_cuts()

    def refresh_manual_crop_list(self) -> None:
        if not hasattr(self, "manual_crop_list"):
            return
        self.manual_crop_list.blockSignals(True)
        self.manual_crop_list.clear()
        for index, box in enumerate(self.split_manual_crops.get(self.split_path_key(), []), start=1):
            left, top, right, bottom = box
            self.manual_crop_list.addItem(f"crop {index:02d} | {right-left} x {bottom-top} | {left},{top},{right},{bottom}")
        self.manual_crop_list.blockSignals(False)

    def add_manual_crop_box(self, box: tuple[int, int, int, int]) -> None:
        if not self.split_current:
            return
        key = self.split_path_key()
        self.split_manual_crops[key] = [box]
        self.refresh_manual_crop_list()
        self.manual_crop_list.setCurrentRow(self.manual_crop_list.count() - 1)
        self.preview_split_cuts()
        self.status.setText(f"Added manual crop for {self.split_current.name}")

    def update_manual_crop_box(self, box: tuple[int, int, int, int]) -> None:
        if not self.split_current:
            return
        if self.cut_mode.currentText() != "Manual crops":
            return
        self.split_manual_crops[self.split_path_key()] = [box]
        self.refresh_manual_crop_list()
        if self.manual_crop_list.count():
            self.manual_crop_list.setCurrentRow(0)
        self.preview_split_cuts()
        self.status.setText(f"Moved manual crop for {self.split_current.name}")

    def update_current_crop_boxes(self, boxes: list[tuple[int, int, int, int]]) -> None:
        if not self.split_current:
            return
        mode = self.cut_mode.currentText()
        key = self.split_path_key()
        normalized = [tuple(box) for box in boxes]
        if mode == "Face crops":
            self.split_face_crops[key] = normalized
            self.preview_split_cuts()
            self.status.setText(f"Edited {len(normalized)} face crop box(es) for {self.split_current.name}")
        elif mode == "Manual crops":
            self.split_manual_crops[key] = normalized[:1]
            self.refresh_manual_crop_list()
            self.preview_split_cuts()

    def delete_selected_manual_crop(self) -> None:
        key = self.split_path_key()
        row = self.manual_crop_list.currentRow()
        crops = self.split_manual_crops.get(key, [])
        if 0 <= row < len(crops):
            del crops[row]
            self.refresh_manual_crop_list()
            if crops:
                self.manual_crop_list.setCurrentRow(min(row, len(crops) - 1))
            self.preview_split_cuts()

    def clear_manual_crops_for_current(self) -> None:
        key = self.split_path_key()
        if key:
            self.split_manual_crops.pop(key, None)
        self.refresh_manual_crop_list()
        self.preview_split_cuts()

    def detect_split_grid(self) -> None:
        if not self.split_current:
            return
        with Image.open(self.split_current) as image:
            rows, cols = detect_grid(image.width, image.height)
        self.split_rows.setValue(rows)
        self.split_cols.setValue(cols)
        self.preview_split_cuts()

    def split_crop(self) -> tuple[int, int, int, int]:
        return (self.crop_left.value(), self.crop_top.value(), self.crop_right.value(), self.crop_bottom.value())

    def split_resize_target(self) -> str:
        if self.split_resize_preset.currentText() == "Custom":
            return self.split_resize_custom.text().strip()
        return self.split_resize_preset.currentText()

    def clamp_box(self, box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
        left, top, right, bottom = box
        left = min(max(0, left), max(0, width - 1))
        top = min(max(0, top), max(0, height - 1))
        right = min(max(left + 1, right), width)
        bottom = min(max(top + 1, bottom), height)
        return (left, top, right, bottom)

    def fit_box_to_ratio(self, box: tuple[int, int, int, int], ratio: float | None, width: int, height: int) -> tuple[int, int, int, int]:
        if not ratio:
            return self.clamp_box(box, width, height)
        left, top, right, bottom = box
        box_w = max(1, right - left)
        box_h = max(1, bottom - top)
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        if box_w / box_h < ratio:
            crop_w = box_h * ratio
            crop_h = box_h
        else:
            crop_w = box_w
            crop_h = box_w / ratio
        crop_w = min(crop_w, width)
        crop_h = min(crop_h, height)
        if crop_w / max(1, crop_h) > ratio:
            crop_w = crop_h * ratio
        else:
            crop_h = crop_w / ratio
        new_left = round(center_x - crop_w / 2)
        new_top = round(center_y - crop_h / 2)
        new_right = round(center_x + crop_w / 2)
        new_bottom = round(center_y + crop_h / 2)
        if new_left < 0:
            new_right -= new_left
            new_left = 0
        if new_top < 0:
            new_bottom -= new_top
            new_top = 0
        if new_right > width:
            new_left -= new_right - width
            new_right = width
        if new_bottom > height:
            new_top -= new_bottom - height
            new_bottom = height
        return self.clamp_box((new_left, new_top, new_right, new_bottom), width, height)

    def framed_face_box(self, face: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
        left, top, right, bottom = face
        face_w = right - left
        face_h = bottom - top
        center_x = left + face_w / 2
        center_y = top + face_h / 2
        padding = self.face_padding.value() / 100.0
        framing = self.face_framing.currentText()
        if framing == "Face tight":
            crop_w = face_w * (1 + padding)
            crop_h = face_h * (1 + padding)
        elif framing == "Head":
            crop_w = face_w * (1.35 + padding)
            crop_h = face_h * (1.55 + padding)
            center_y -= face_h * 0.08
        elif framing == "Square portrait":
            side = max(face_w, face_h) * (2.0 + padding)
            crop_w = crop_h = side
            center_y += face_h * 0.20
        else:
            crop_w = face_w * (2.0 + padding)
            crop_h = face_h * (2.45 + padding)
            center_y += face_h * 0.45
        framed = self.clamp_box((round(center_x - crop_w / 2), round(center_y - crop_h / 2), round(center_x + crop_w / 2), round(center_y + crop_h / 2)), width, height)
        return self.fit_box_to_ratio(framed, self.crop_ratio_value(), width, height)

    def detect_face_boxes(self, path: Path) -> tuple[list[tuple[int, int, int, int]], str]:
        try:
            import cv2  # type: ignore
        except Exception:
            return [], "OpenCV is not installed. Install opencv-python to enable local face detection."
        image = cv2.imread(str(path))
        if image is None:
            return [], f"Could not read image: {path.name}"
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(str(cascade_path))
        if detector.empty():
            return [], "OpenCV Haar cascade could not be loaded."
        min_size = self.face_min_size.value()
        detected = detector.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(min_size, min_size))
        height, width = gray.shape[:2]
        boxes = [self.framed_face_box((int(x), int(y), int(x + w), int(y + h)), width, height) for x, y, w, h in detected]
        return boxes, ""

    def detect_faces_for_current(self) -> None:
        if not self.split_current:
            return
        boxes, error = self.detect_face_boxes(self.split_current)
        key = self.split_path_key()
        self.split_face_crops[key] = boxes
        self.cut_mode.setCurrentText("Face crops")
        self.preview_split_cuts()
        if error:
            self.split_log.setPlainText(error)
        else:
            self.split_log.setPlainText(f"Detected {len(boxes)} face crop(s) in {self.split_current.name}. Review boxes before export.")

    def detect_faces_for_all(self) -> None:
        if not self.split_inputs:
            return
        log: list[str] = []
        total = 0
        self.begin_progress("Detecting faces", len(self.split_inputs))
        for step, path in enumerate(self.split_inputs, start=1):
            boxes, error = self.detect_face_boxes(path)
            self.split_face_crops[normalized_path_key(path)] = boxes
            total += len(boxes)
            log.append(f"{'FAILED' if error else 'OK'} {path.name}: {error or f'{len(boxes)} face crop(s)'}")
            self.update_progress(step, f"Detecting faces: {path.name}")
        self.cut_mode.setCurrentText("Face crops")
        self.preview_split_cuts()
        self.split_log.setPlainText("\n".join(log))
        self.end_progress(f"Detected {total} face crop(s) across {len(self.split_inputs)} image(s)")

    def preview_split_cuts(self) -> None:
        if not self.split_current:
            return
        mode = self.cut_mode.currentText()
        output = self.split_output.text() or self.split_current.parent / Path(self.folder_rel("split")).name
        if mode == "Grid / Sheet":
            self.split_preview.set_boxes([], draw_grid=False)
            self.split_preview.set_grid(self.split_rows.value(), self.split_cols.value(), self.split_crop())
            with Image.open(self.split_current) as image:
                boxes = grid_boxes(image.width, image.height, self.split_rows.value(), self.split_cols.value(), self.split_crop())
            first = boxes[0]
            self.split_info.setText(f"{self.split_current.name} | grid | {len(boxes)} cuts | first {first[2]-first[0]} x {first[3]-first[1]} px | output {output}")
            return
        boxes = self.current_mode_boxes()
        self.split_preview.set_boxes(boxes, draw_grid=False)
        mode_label = "face" if mode == "Face crops" else "manual"
        if boxes:
            first = boxes[0]
            self.split_info.setText(f"{self.split_current.name} | {mode_label} | {len(boxes)} crop(s) | first {first[2]-first[0]} x {first[3]-first[1]} px | output {output}")
        else:
            hint = "Click Detect Faces to suggest boxes." if mode == "Face crops" else "Drag on the preview to add crop boxes."
            self.split_info.setText(f"{self.split_current.name} | {mode_label} | no crops yet | {hint}")

    def choose_split_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose split output folder", str(Path(self.split_output.text() or Path.home())))
        if folder:
            self.split_output.setText(folder)

    def export_split_cuts(self) -> None:
        if self.split_thread is not None and self.split_thread.isRunning():
            QMessageBox.information(self, APP_NAME, "Cut export is already running.")
            return
        if not self.split_inputs:
            self.load_split_images()
            if not self.split_inputs:
                return
        mode = self.cut_mode.currentText()
        total_sources = len(self.split_inputs)
        self.cancel_requested = False
        if hasattr(self, "split_play_button"):
            self.split_play_button.setEnabled(False)
        if hasattr(self, "split_stop_button"):
            self.split_stop_button.setEnabled(True)
        self.begin_progress("Exporting cuts", total_sources)
        final_export_dir = self.project_folder("export") if self.dataset_root is not None else None
        self.split_thread = QThread(self)
        self.split_worker = SplitExportWorker(
            inputs=list(self.split_inputs),
            mode=mode,
            output_text=self.split_output.text().strip(),
            split_folder_name=Path(self.folder_rel("split")).name,
            auto_detect=self.auto_detect.isChecked(),
            rows=self.split_rows.value(),
            cols=self.split_cols.value(),
            crop=self.split_crop(),
            face_crops={key: list(value) for key, value in self.split_face_crops.items()},
            manual_crops={key: list(value) for key, value in self.split_manual_crops.items()},
            naming_pattern=self.naming_pattern.currentText(),
            final_export_dir=final_export_dir,
            resize_final=self.split_resize.isChecked(),
            resize_target=self.split_resize_target(),
            resize_mode=self.resize_mode.currentText() if hasattr(self, "resize_mode") else "Keep aspect ratio",
        )
        self.split_worker.moveToThread(self.split_thread)
        self.split_thread.started.connect(self.split_worker.run)
        self.split_worker.progress.connect(self.update_progress)
        self.split_worker.finished.connect(self.split_export_finished)
        self.split_worker.finished.connect(self.split_thread.quit)
        self.split_worker.finished.connect(self.split_worker.deleteLater)
        self.split_thread.finished.connect(self.split_thread.deleteLater)
        self.split_thread.finished.connect(self.clear_split_worker_refs)
        self.split_thread.start()

    def clear_split_worker_refs(self) -> None:
        self.split_thread = None
        self.split_worker = None

    def split_export_finished(self, created: list[Path], log: list[str], cancelled: bool, copied: int, copy_failed: list[str], _export_dir: str) -> None:
        self.split_outputs = created
        self.split_log.setPlainText("\n".join(log))
        if hasattr(self, "split_play_button"):
            self.split_play_button.setEnabled(True)
        if hasattr(self, "split_stop_button"):
            self.split_stop_button.setEnabled(False)
        if cancelled:
            self.end_progress(f"Stopped export. Kept {len(created)} completed cut image(s)")
        else:
            self.end_progress(f"Exported {len(created)} cut image(s)")
        if copy_failed:
            QMessageBox.warning(self, APP_NAME, "Some final export copies failed:\n\n" + "\n".join(copy_failed[:20]))
        if created and self.dataset_root is not None and copied:
            self.load_current_dataset_images()
        self.cancel_requested = False

    def choose_dataset_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select project folder", str(DEFAULT_DATASETS_DIR))
        if folder:
            self.open_project_root(Path(folder), save_last=True)

    def load_dataset_source_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Load images from source folder", str(Path.home()))
        if folder:
            self.load_dataset_images(Path(folder))

    def load_current_dataset_images(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        self.load_dataset_images(self.current_prepped_folder(root))

    def load_dataset_images_from_paths(self, paths: list[Path]) -> None:
        files = image_paths_from_items(paths)
        self.populate_dataset_list(files)

    def load_dataset_images(self, folder: Path) -> None:
        if self.dataset_root is not None:
            self.ensure_dataset_structure(save=False)
        self.populate_dataset_list(image_paths_from_items([folder]))

    def populate_dataset_list(self, files: list[Path]) -> None:
        self.dataset_list.clear()
        if not files:
            self.dataset_list.show_empty()
            return
        self.begin_progress("Loading review thumbnails", len(files))
        for index, path in enumerate(files, start=1):
            bucket = self.manifest.record_for(path.name).get("bucket", "Needs Review")
            self.dataset_list.addItem(thumb_item(path, f"{path.name}  [{bucket}]"))
            self.update_progress(index, f"Loading review thumbnail: {path.name}")
        self.dataset_list.setCurrentRow(0)
        self.end_progress(f"Loaded {len(files)} review image(s)")

    def dataset_selection_changed(self, current: QListWidgetItem | None) -> None:
        path = Path(current.data(Qt.UserRole)) if current and current.data(Qt.UserRole) else None
        self.current_dataset_image = path
        self.dataset_preview.set_image(path)
        if not path:
            return
        record = self.manifest.record_for(path.name)
        self.caption_editor.setPlainText(record.get("caption", self.read_caption(path)))
        self.reason_tags.setText(", ".join(record.get("reason_tags", [])))

    def classify_selected(self, bucket: str) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        selected = [Path(item.data(Qt.UserRole)) for item in self.dataset_list.selectedItems() if item.data(Qt.UserRole)]
        if not selected and self.current_dataset_image:
            selected = [self.current_dataset_image]
        if not selected:
            return
        dest_map = {"rejected": "rejected", "broad": "broad", "strict": "strict"}
        tags = [tag.strip() for tag in self.reason_tags.text().split(",") if tag.strip()]
        for path in selected:
            record = self.manifest.record_for(path.name)
            record["bucket"] = FOLDER_PREFERENCE_LABELS.get(bucket, bucket)
            record["reason_tags"] = tags
            if bucket in dest_map:
                dest = unique_path(self.project_folder(dest_map[bucket], root) / path.name)
                shutil.copy2(path, dest)
                cap = self.read_caption(path)
                if cap:
                    dest.with_suffix(CAPTION_EXT).write_text(cap, encoding="utf-8")
        self.manifest.save(f"classified {len(selected)} image(s) as {FOLDER_PREFERENCE_LABELS.get(bucket, bucket)}")
        self.populate_dataset_list([Path(self.dataset_list.item(i).data(Qt.UserRole)) for i in range(self.dataset_list.count()) if self.dataset_list.item(i).data(Qt.UserRole)])

    def read_caption(self, image_path: Path) -> str:
        cap_path = image_path.with_suffix(CAPTION_EXT)
        if cap_path.exists():
            return cap_path.read_text(encoding="utf-8", errors="replace").strip()
        return ""

    def save_caption_for_current(self) -> None:
        if self.require_dataset_root() is None:
            return
        if not self.current_dataset_image:
            return
        caption = self.caption_editor.toPlainText().strip()
        tags = [tag.strip() for tag in self.reason_tags.text().split(",") if tag.strip()]
        self.current_dataset_image.with_suffix(CAPTION_EXT).write_text(caption, encoding="utf-8")
        record = self.manifest.record_for(self.current_dataset_image.name)
        record["caption"] = caption
        record["reason_tags"] = tags
        self.manifest.save(f"caption saved for {self.current_dataset_image.name}")
        self.status.setText("Caption saved")

    def generate_captions(self) -> None:
        if self.caption_thread is not None and self.caption_thread.isRunning():
            QMessageBox.information(self, APP_NAME, "Caption generation is already running.")
            return
        root = self.require_dataset_root()
        if root is None:
            return
        trigger = self.trigger_edit.text().strip()
        if not trigger:
            QMessageBox.warning(self, APP_NAME, "Enter a trigger token first.")
            return
        self.manifest.data["trigger"] = trigger
        self.manifest.data["caption_mode"] = self.caption_mode.currentText()
        selected = [Path(item.data(Qt.UserRole)) for item in self.dataset_list.selectedItems() if item.data(Qt.UserRole)]
        prepped_dir = self.current_prepped_folder(root)
        images = selected or image_paths_from_items([prepped_dir])
        if not images:
            QMessageBox.information(self, APP_NAME, f"Select images or export images to {prepped_dir} first.")
            return
        mode = self.caption_mode.currentText()
        settings = json.loads(json.dumps(self.settings))
        self.begin_progress("Generating captions", len(images))
        self.cancel_requested = False
        self.caption_thread = QThread(self)
        self.caption_worker = CaptionWorker(self.make_caption, images, trigger, mode, settings)
        self.caption_worker.moveToThread(self.caption_thread)
        self.caption_thread.started.connect(self.caption_worker.run)
        self.caption_worker.progress.connect(self.update_progress)
        self.caption_worker.finished.connect(self.caption_generation_finished)
        self.caption_worker.finished.connect(self.caption_thread.quit)
        self.caption_worker.finished.connect(self.caption_worker.deleteLater)
        self.caption_thread.finished.connect(self.caption_thread.deleteLater)
        self.caption_thread.finished.connect(self.clear_caption_worker_refs)
        self.caption_thread.start()

    def clear_caption_worker_refs(self) -> None:
        self.caption_thread = None
        self.caption_worker = None

    def caption_generation_finished(self, made: int, failed: list[str], records: list[tuple[str, str]], cancelled: bool, mode: str) -> None:
        for filename, caption in records:
            record = self.manifest.record_for(filename)
            record["caption"] = caption
        action = f"generated {made} caption(s) with {mode}"
        if cancelled:
            action = f"stopped caption generation after {made} caption(s) with {mode}"
        if failed:
            action += f"; skipped {len(failed)} failed file(s)"
            QMessageBox.warning(self, APP_NAME, "Some captions could not be generated:\n\n" + "\n".join(failed[:20]))
        self.manifest.save(action)
        self.end_progress(action)

    def caption_prompt_text(self, trigger: str, settings: dict[str, Any]) -> str:
        template = settings.get("caption_template", DEFAULT_CAPTION_TEMPLATE)
        template = template.replace("<trigger>", trigger)
        profile = settings.get("training_target_profile", "Unknown/custom")
        prompt = settings.get("caption_prompt", DEFAULT_CAPTION_PROMPT)
        return (
            prompt.replace("<trigger>", trigger)
            .replace("<profile>", profile)
            .replace("<template>", template)
        )

    def make_caption(self, image_path: Path, trigger: str, mode: str, settings: dict[str, Any]) -> str:
        prompt = self.caption_prompt_text(trigger, settings)
        if mode == "API model":
            return self.force_trigger(self.caption_with_api_model(image_path, trigger, prompt, settings), trigger)
        if mode == "Local server":
            return self.force_trigger(self.caption_with_local_server(image_path, trigger, prompt, settings), trigger)
        if mode == "Local model":
            local_command = settings.get("local_caption_command", "").strip()
            if local_command:
                return self.force_trigger(self.run_caption_command(local_command, image_path, trigger, prompt, settings), trigger)
            model_type = settings.get("local_model_type", "Local model")
            model_path = settings.get("model_path", "")
            if "Qwen3-VL" in model_type:
                return self.force_trigger(self.caption_with_qwen_vl(image_path, prompt, settings), trigger)
            raise RuntimeError(f"local model backend not configured for {model_type} at {model_path}. Use Custom command or set local_caption_command in settings.json.")
        if mode == "Custom command":
            text = self.run_caption_command(settings.get("caption_command", ""), image_path, trigger, prompt, settings)
            if text:
                return self.force_trigger(text, trigger)
            raise RuntimeError("caption command returned empty text")
        template = settings.get("caption_template", DEFAULT_CAPTION_TEMPLATE)
        caption = (
            template.replace("<trigger>", trigger)
            .replace("<subject_type>", "person")
            .replace("<framing>", "centered portrait")
            .replace("<angle>", "front view")
            .replace("<direction>", "looking forward")
            .replace("<expression>", "neutral expression")
            .replace("<hair>", "visible hair")
            .replace("<outfit>", "visible outfit")
            .replace("<setting>", "simple setting")
            .replace("<lighting>", "natural lighting")
        )
        return self.force_trigger(caption, trigger)

    def run_caption_command(self, command_template: str, image_path: Path, trigger: str, prompt: str, settings: dict[str, Any]) -> str:
        command = command_template.format(image=str(image_path), trigger=trigger, prompt=prompt)
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=int(settings.get("caption_timeout", 120)))
        text = result.stdout.strip()
        if not text and result.stderr.strip():
            raise RuntimeError(result.stderr.strip()[:500])
        if text.startswith("{"):
            data = json.loads(text)
            text = str(data.get(settings.get("caption_json_field", "caption"), ""))
        return text

    def caption_with_qwen_vl(self, image_path: Path, prompt: str, settings: dict[str, Any]) -> str:
        model_path = Path(settings.get("model_path", "")).resolve()
        if not model_path.exists():
            raise RuntimeError(f"local Qwen model path does not exist: {model_path}")
        if "gguf" in model_path.name.lower():
            raise RuntimeError("Qwen3-VL GGUF models need a llama.cpp/Ollama-style command runner. Select a Transformers-format Qwen model or use Custom command.")
        try:
            import torch  # type: ignore
            from transformers import AutoModelForImageTextToText, AutoProcessor  # type: ignore
            from qwen_vl_utils import process_vision_info  # type: ignore
        except Exception as exc:
            if getattr(sys, "frozen", False):
                raise RuntimeError("Direct Transformers local models are not bundled in the clean build. Use Caption mode: Local server with Ollama, LM Studio, KoboldCPP, or a custom local endpoint.") from exc
            raise RuntimeError("Install local caption dependencies first: python -m pip install torch transformers accelerate qwen-vl-utils") from exc

        cache_key = str(model_path)
        if cache_key not in self.local_caption_cache:
            device_pref = settings.get("device", "Auto")
            has_cuda = bool(getattr(torch.cuda, "is_available", lambda: False)())
            if device_pref == "CPU":
                device_map: str | dict[str, str] = "cpu"
                dtype = torch.float32
            else:
                device_map = "auto" if device_pref == "Auto" else "cuda"
                dtype = torch.bfloat16 if has_cuda else torch.float32
            processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
            model = AutoModelForImageTextToText.from_pretrained(
                str(model_path),
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
            )
            self.local_caption_cache[cache_key] = {"processor": processor, "model": model}

        bundle = self.local_caption_cache[cache_key]
        processor = bundle["processor"]
        model = bundle["model"]
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        try:
            inputs = inputs.to(model.device)
        except Exception:
            pass
        output_ids = model.generate(**inputs, max_new_tokens=160)
        input_len = inputs["input_ids"].shape[-1]
        generated = output_ids[:, input_len:]
        result = processor.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
        return result

    def image_data_url(self, image_path: Path) -> tuple[str, str]:
        suffix = image_path.suffix.lower().lstrip(".")
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix or 'png'}"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}", encoded

    def provider_api_key(self, settings: dict[str, Any], provider: str) -> str:
        key_name = provider.lower().split()[0]
        keys = settings.get("provider_api_keys", {})
        return keys.get(key_name, "")

    def api_error_message(self, status_code: int, body: str) -> tuple[str, bool]:
        try:
            data = json.loads(body)
            error = data.get("error", data)
            message = str(error.get("message", body)).strip()
            code = str(error.get("code", "")).strip()
            if code == "insufficient_quota":
                return (
                    "OpenAI API quota/billing is not available for this key. Check the OpenAI account billing plan, usage limits, or use a different API key in Settings.",
                    False,
                )
            if code:
                message = f"{message} ({code})"
            return f"HTTP {status_code}: {message}", status_code in {429, 500, 502, 503, 504}
        except Exception:
            return f"HTTP {status_code}: {body[:700]}", status_code in {429, 500, 502, 503, 504}

    def post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        last_error = ""
        for attempt in range(3):
            request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error, should_retry = self.api_error_message(exc.code, body)
                if not should_retry or attempt == 2:
                    raise RuntimeError(last_error) from exc
                time.sleep(1.5 * (attempt + 1))
            except urllib.error.URLError as exc:
                last_error = str(exc)
                if attempt == 2:
                    raise RuntimeError(last_error) from exc
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(last_error or "request failed")

    def caption_with_local_server(self, image_path: Path, trigger: str, prompt: str, settings: dict[str, Any]) -> str:
        provider = settings.get("local_server_provider", "Ollama")
        url = settings.get("local_server_url", "").strip()
        model = settings.get("local_server_model", "").strip()
        timeout = int(settings.get("caption_timeout", 120))
        data_url, image_b64 = self.image_data_url(image_path)
        if not url:
            raise RuntimeError(f"missing local server URL for {provider}")
        if provider == "Ollama":
            if not model:
                raise RuntimeError("missing Ollama model name")
            if url.rstrip("/").endswith("/api/chat"):
                payload = {
                    "model": model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
                }
                data = self.post_json(url, payload, {}, timeout)
                message = data.get("message", {})
                return str(message.get("content", data.get("response", ""))).strip()
            payload = {"model": model, "prompt": prompt, "images": [image_b64], "stream": False}
            data = self.post_json(url, payload, {}, timeout)
            return str(data.get("response", "")).strip()
        if provider in {"LM Studio", "KoboldCPP", "Custom OpenAI-compatible"}:
            if not model:
                raise RuntimeError(f"missing {provider} model name")
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.2,
            }
            data = self.post_json(url, payload, {}, timeout)
            return self.extract_chat_completion_text(data)
        data = self.post_json(
            url,
            {"image": str(image_path), "image_base64": image_b64, "image_url": data_url, "trigger": trigger, "prompt": prompt, "model": model},
            {},
            timeout,
        )
        return str(data.get(settings.get("caption_json_field", "caption"), data.get("caption", data.get("text", "")))).strip()

    def caption_with_api_model(self, image_path: Path, trigger: str, prompt: str, settings: dict[str, Any]) -> str:
        provider = settings.get("api_provider", "OpenAI")
        api_key = self.provider_api_key(settings, provider)
        if not api_key:
            raise RuntimeError(f"missing {provider} API key")
        timeout = int(settings.get("caption_timeout", 120))
        model = settings.get("api_model", "").strip()
        data_url, image_b64 = self.image_data_url(image_path)
        if provider == "OpenAI":
            payload = {
                "model": model or "gpt-4o-mini",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
            }
            data = self.post_json("https://api.openai.com/v1/responses", payload, {"Authorization": f"Bearer {api_key}"}, timeout)
            return self.extract_openai_text(data)
        if provider == "Gemini":
            mime = data_url.split(";", 1)[0].replace("data:", "")
            payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": image_b64}}]}]}
            gemini_model = model or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
            data = self.post_json(url, payload, {}, timeout)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if provider == "Anthropic":
            mime = data_url.split(";", 1)[0].replace("data:", "")
            payload = {
                "model": model or "claude-3-5-sonnet-latest",
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": image_b64}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            }
            data = self.post_json("https://api.anthropic.com/v1/messages", payload, {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout)
            return data["content"][0]["text"]
        custom_url = settings.get("custom_api_url", "").strip()
        if not custom_url:
            raise RuntimeError("missing custom_api_url in settings.json")
        data = self.post_json(custom_url, {"image": str(image_path), "image_base64": image_b64, "trigger": trigger, "prompt": prompt}, {"Authorization": f"Bearer {api_key}"}, timeout)
        return str(data.get(settings.get("caption_json_field", "caption"), data.get("caption", "")))

    def extract_chat_completion_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(str(item))
                return " ".join(part for part in parts if part).strip()
            return str(content).strip()
        return str(data.get("response", data.get("text", ""))).strip()

    def extract_openai_text(self, data: dict[str, Any]) -> str:
        if data.get("output_text"):
            return str(data["output_text"])
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    chunks.append(str(content["text"]))
        return " ".join(chunks).strip()

    def force_trigger(self, caption: str, trigger: str) -> str:
        cleaned = caption.strip()
        prefix = f"{trigger},"
        if cleaned == trigger:
            return prefix
        if cleaned.startswith(prefix):
            return cleaned
        return f"{prefix} {cleaned.lstrip(', ')}"

    def export_size_text(self) -> str:
        return self.custom_export_size.text() if self.export_size.currentText() == "Custom" else self.export_size.currentText()

    def copy_images_to_prepped(self, images: list[Path], action_label: str, size_override: str | None = None) -> tuple[int, list[str], Path]:
        root = self.require_dataset_root()
        if root is None:
            return 0, [], DEFAULT_DATASETS_DIR
        trigger = self.trigger_edit.text().strip()
        size_text = size_override or self.export_size_text()
        export_dir = self.project_folder("export", root)
        export_dir.mkdir(parents=True, exist_ok=True)
        exported = 0
        failed: list[str] = []
        self.begin_progress(action_label, len(images))
        for index, image_path in enumerate(images, start=1):
            try:
                if image_path.stat().st_size <= 0:
                    raise ValueError("empty file")
                out_path = unique_path(export_dir / image_path.name)
                with Image.open(image_path) as image:
                    out = resize_image(image.convert("RGB"), size_text, self.resize_mode.currentText())
                    out.save(out_path)
                cap = self.read_caption(image_path)
                if cap:
                    clean_caption = self.force_trigger(cap, trigger) if trigger else cap
                    out_path.with_suffix(CAPTION_EXT).write_text(clean_caption, encoding="utf-8")
                exported += 1
            except Exception as exc:
                failed.append(f"{image_path.name}: {exc}")
            self.update_progress(index, f"{action_label}: {image_path.name}")
        if trigger:
            self.manifest.data["trigger"] = trigger
        self.manifest.data["export"] = {"size": size_text, "resize_mode": self.resize_mode.currentText(), "folder": str(export_dir)}
        self.manifest.data["dataset"]["last_exported"] = timestamp()
        action = f"{action_label}: {exported} image(s) to {export_dir}"
        if failed:
            action += f"; skipped {len(failed)} failed file(s)"
            QMessageBox.warning(self, APP_NAME, "Some files could not be exported:\n\n" + "\n".join(failed[:20]))
        self.manifest.save(action)
        self.end_progress(action)
        return exported, failed, export_dir

    def resize_final_export_folder(self, folder: Path) -> tuple[int, list[str]]:
        images = image_paths_from_items([folder])
        if not images:
            QMessageBox.warning(self, APP_NAME, f"No images found in final export folder:\n\n{folder}")
            return 0, []
        trigger = self.trigger_edit.text().strip()
        size_text = self.export_size_text()
        exported = 0
        failed: list[str] = []
        self.begin_progress("Updating final export folder", len(images))
        for index, image_path in enumerate(images, start=1):
            try:
                if image_path.stat().st_size <= 0:
                    raise ValueError("empty file")
                if size_text != "Original":
                    with Image.open(image_path) as image:
                        out = resize_image(image.convert("RGB"), size_text, self.resize_mode.currentText())
                        out.save(image_path)
                cap = self.read_caption(image_path)
                if cap and trigger:
                    image_path.with_suffix(CAPTION_EXT).write_text(self.force_trigger(cap, trigger), encoding="utf-8")
                exported += 1
            except Exception as exc:
                failed.append(f"{image_path.name}: {exc}")
            self.update_progress(index, f"Updating final export folder: {image_path.name}")
        if trigger:
            self.manifest.data["trigger"] = trigger
        self.manifest.data["export"] = {"size": size_text, "resize_mode": self.resize_mode.currentText(), "folder": str(folder)}
        self.manifest.data["dataset"]["last_exported"] = timestamp()
        action = f"updated {exported} final export image(s) in {folder}"
        if failed:
            action += f"; skipped {len(failed)} failed file(s)"
            QMessageBox.warning(self, APP_NAME, "Some final export files could not be updated:\n\n" + "\n".join(failed[:20]))
        self.manifest.save(action)
        self.end_progress(action)
        return exported, failed

    def export_dataset(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        self.resize_final_export_folder(self.current_prepped_folder(root))
        self.load_current_dataset_images()

    def validate_dataset(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        report = self.dataset_validation_report(root)
        QMessageBox.information(self, "Validation Report", "\n".join(report))
        self.status.setText("Validation complete")

    def dataset_validation_report(self, root: Path) -> list[str]:
        trigger = self.trigger_edit.text().strip() or Manifest(root).data.get("trigger", "")
        strict = self.project_folder("strict", root)
        split = self.project_folder("split", root)
        prepped = self.current_prepped_folder(root)
        images = image_paths_from_items([prepped])
        caps = list(prepped.glob(f"*{CAPTION_EXT}")) if prepped.exists() else []
        image_stems = {p.stem for p in images}
        cap_stems = {p.stem for p in caps}
        duplicates = sorted({p.name for p in images if sum(1 for q in images if q.name.lower() == p.name.lower()) > 1})
        bad_prefix = [p.name for p in caps if trigger and not p.read_text(encoding="utf-8", errors="replace").strip().startswith(f"{trigger},")]
        wrong_dims: list[str] = []
        target = self.export_size_text() if hasattr(self, "export_size") else "Original"
        if target != "Original":
            try:
                expected = parse_size(target)
                for image_path in image_paths_from_items([prepped]):
                    with Image.open(image_path) as image:
                        if image.size != expected:
                            wrong_dims.append(f"{image_path.name} {image.size[0]}x{image.size[1]}")
            except Exception:
                pass
        return [
            f"Project: {root}",
            f"Trigger: {trigger or 'MISSING'}",
            f"Split image count: {len(image_paths_from_items([split]))}",
            f"Strict source count: {len(image_paths_from_items([strict]))}",
            f"Prepped folder: {prepped}",
            f"Prepped image count: {len(images)}",
            f"Caption count: {len(caps)}",
            f"Missing captions: {', '.join(sorted(image_stems - cap_stems)) or 'none'}",
            f"Orphan captions: {', '.join(sorted(cap_stems - image_stems)) or 'none'}",
            f"Bad trigger prefixes: {', '.join(bad_prefix) or 'none'}",
            f"Wrong exported dimensions: {', '.join(wrong_dims) or 'none'}",
            f"Duplicate names: {', '.join(duplicates) or 'none'}",
        ]

    def make_contact_sheet(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        selected = [Path(item.data(Qt.UserRole)) for item in self.dataset_list.selectedItems() if item.data(Qt.UserRole)]
        images = selected or [Path(self.dataset_list.item(i).data(Qt.UserRole)) for i in range(self.dataset_list.count()) if self.dataset_list.item(i).data(Qt.UserRole)]
        if not images:
            return
        thumb = 180
        cols = 5
        rows = (len(images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 28)), (16, 16, 16))
        self.begin_progress("Making contact sheet", len(images))
        for idx, path in enumerate(images):
            with Image.open(path) as image:
                cell = ImageOps.pad(image.convert("RGB"), (thumb, thumb), method=Image.Resampling.LANCZOS)
            x = (idx % cols) * thumb
            y = (idx // cols) * (thumb + 28)
            sheet.paste(cell, (x, y))
            self.update_progress(idx + 1, f"Making contact sheet: {path.name}")
        out = unique_path(root / f"contact_sheet_{timestamp()}.jpg")
        sheet.save(out, quality=92)
        open_folder(out.parent)
        self.end_progress(f"Contact sheet saved: {out}")

    def add_anchor(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Add anchor/reference images", str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        anchors = self.project_folder("anchors", root)
        anchors.mkdir(parents=True, exist_ok=True)
        for file in files:
            src = Path(file)
            shutil.copy2(src, unique_path(anchors / src.name))
        self.refresh_anchors()

    def refresh_anchors(self) -> None:
        self.anchor_combo.clear()
        self.anchor_combo.addItem("")
        if self.dataset_root is None:
            return
        for path in image_paths_from_items([self.project_folder("anchors")]):
            self.anchor_combo.addItem(path.name, str(path))

    def show_anchor(self) -> None:
        path = Path(self.anchor_combo.currentData()) if self.anchor_combo.currentData() else None
        self.anchor_preview.set_image(path)

    def open_caption_settings(self) -> None:
        dialog = CaptionSettingsDialog(self.settings, self)
        if dialog.exec():
            save_settings(self.settings)
            self.caption_mode.setCurrentText(self.settings.get("caption_mode", "Manual / Template only"))
            self.manifest.data["caption_mode"] = self.caption_mode.currentText()
            self.manifest.data["training_target_profile"] = self.settings.get("training_target_profile", "Unknown/custom")
            self.manifest.save("caption settings updated")

    def selected_library_root(self) -> Path | None:
        item = self.library_list.currentItem()
        return Path(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def load_library_details(self, root: Path | None) -> None:
        if not hasattr(self, "library_manifest_view"):
            return
        self.library_thumbs.clear()
        self.library_preview.set_image(None)
        if root is None:
            self.library_summary.setText("Select a project to inspect.")
            self.library_manifest_view.clear()
            self.library_thumbs.show_empty()
            return

        manifest = Manifest(root)
        manifest_text = json.dumps(manifest.data, indent=2)
        self.library_manifest_view.setPlainText(manifest_text)
        counts = {
            "project_images": len(image_paths_from_items([self.project_folder("project_images", root)])),
            "broad": len(image_paths_from_items([self.project_folder("broad", root)])),
            "strict": len(image_paths_from_items([self.project_folder("strict", root)])),
            "export": len(image_paths_from_items([self.project_folder("export", root)])),
        }
        trigger = manifest.data.get("trigger", "") or "none"
        export = manifest.data.get("export", {})
        self.library_summary.setText(
            f"{root.name} | trigger {trigger} | images {counts['project_images']} | 0.use {counts['broad']} | "
            f"0.useV2 {counts['strict']} | prepped {counts['export']} | export {export.get('size', 'not exported')} | {root}"
        )
        prepped_images = image_paths_from_items([self.current_prepped_folder(root)])
        if not prepped_images:
            self.library_thumbs.show_empty()
            return
        self.begin_progress("Loading library thumbnails", len(prepped_images))
        for index, path in enumerate(prepped_images, start=1):
            self.library_thumbs.addItem(library_thumb_item(path))
            self.update_progress(index, f"Loading library thumbnail: {path.name}")
        self.library_thumbs.setCurrentRow(0)
        self.end_progress(f"Loaded {len(prepped_images)} library thumbnail(s)")

    def library_selection_changed(self, current: QListWidgetItem | None) -> None:
        root = Path(current.data(Qt.UserRole)) if current and current.data(Qt.UserRole) else None
        self.load_library_details(root)

    def library_thumbnail_changed(self, current: QListWidgetItem | None) -> None:
        path = Path(current.data(Qt.UserRole)) if current and current.data(Qt.UserRole) else None
        self.library_preview.set_image(path)

    def refresh_library(self) -> None:
        self.refresh_project_combo()
        current_key = normalized_path_key(self.selected_library_root()) if self.selected_library_root() else ""
        self.library_list.clear()
        seen: set[str] = set()
        selected_row = -1
        roots = self.known_project_roots()
        if roots:
            self.begin_progress("Refreshing library", len(roots))
        for index, root in enumerate(roots, start=1):
            key = normalized_path_key(root)
            if key in seen:
                continue
            seen.add(key)
            manifest = Manifest(root)
            data = manifest.data
            counts = {
                "broad": len(image_paths_from_items([self.project_folder("broad", root)])),
                "strict": len(image_paths_from_items([self.project_folder("strict", root)])),
                "export": len(image_paths_from_items([self.project_folder("export", root)])),
            }
            export = data.get("export", {})
            name = data.get("dataset", {}).get("name") or root.name
            trigger = data.get("trigger", "") or "none"
            size = export.get("size", "") or "not exported"
            label = f"{name} | trigger {trigger} | 0.use {counts['broad']} | 0.useV2 {counts['strict']} | prepped {counts['export']} | size {size} | {root}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(root))
            self.library_list.addItem(item)
            if current_key and normalized_path_key(root) == current_key:
                selected_row = self.library_list.count() - 1
            self.update_progress(index, f"Refreshing library: {root.name}")
        if selected_row >= 0:
            self.library_list.setCurrentRow(selected_row)
        elif self.library_list.count():
            self.library_list.setCurrentRow(0)
        else:
            self.load_library_details(None)
        if roots:
            self.end_progress(f"Library refreshed: {len(roots)} project(s)")

    def add_custom_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add custom project library root", str(Path.home()))
        if folder:
            roots = self.settings.setdefault("custom_dataset_roots", [])
            new_path = Path(folder)
            new_key = normalized_path_key(new_path)
            existing_keys = {normalized_path_key(DEFAULT_DATASETS_DIR)}
            existing_keys.update(normalized_path_key(Path(path)) for path in roots)
            if new_key in existing_keys:
                QMessageBox.information(self, APP_NAME, f"This project library root is already added:\n\n{new_path}")
                return
            roots.append(str(new_path))
            save_settings(self.settings)
            self.refresh_library()

    def open_library_dataset(self) -> None:
        root = self.selected_library_root()
        if root:
            self.open_project_root(root, save_last=True)
            for index in range(self.tabs.count()):
                if self.tabs.tabText(index) == "Dataset Prep":
                    self.tabs.setCurrentIndex(index)
                    break

    def open_library_folder(self, rel: str) -> None:
        root = self.selected_library_root()
        if root:
            open_folder(root / rel)

    def open_library_folder_key(self, key: str) -> None:
        root = self.selected_library_root()
        if root:
            open_folder(self.project_folder(key, root))

    def validate_library_dataset(self) -> None:
        root = self.selected_library_root()
        if root:
            QMessageBox.information(self, "Validation Report", "\n".join(self.dataset_validation_report(root)))

    def edit_library_manifest(self) -> None:
        root = self.selected_library_root()
        if root and (root / "manifest.json").exists():
            os.startfile(root / "manifest.json")

    def hide_library_dataset(self) -> None:
        root = self.selected_library_root()
        if root:
            hidden = self.settings.setdefault("hidden_datasets", [])
            hidden.append(str(root))
            save_settings(self.settings)
            self.refresh_library()

    def open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(1040, 820)
        dialog.setMinimumWidth(960)
        outer_layout = QVBoxLayout(dialog)
        content = QWidget()
        layout = QFormLayout(content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer_layout.addWidget(scroll, 1)
        toolkit = QLineEdit(self.settings.get("ostris_toolkit_path", ""))
        model_locations = QPlainTextEdit("\n".join(self.settings.get("caption_model_locations", [str(DEFAULT_MODELS_DIR)])))
        roots = QPlainTextEdit("\n".join(self.settings.get("custom_dataset_roots", [])))
        api_keys = self.settings.get("provider_api_keys", {})
        hf_key = QLineEdit(api_keys.get("huggingface", ""))
        civitai_key = QLineEdit(api_keys.get("civitai", ""))
        openai_key = QLineEdit(api_keys.get("openai", ""))
        gemini_key = QLineEdit(api_keys.get("gemini", ""))
        anthropic_key = QLineEdit(api_keys.get("anthropic", ""))
        custom_key = QLineEdit(api_keys.get("custom", ""))
        custom_name = QLineEdit(self.settings.get("custom_api_provider_name", "Custom HTTP"))
        custom_url = QLineEdit(self.settings.get("custom_api_url", ""))
        for key_field in [hf_key, civitai_key, openai_key, gemini_key, anthropic_key, custom_key]:
            key_field.setEchoMode(QLineEdit.Password)
        theme_values = dict(THEME)
        theme_values.update(self.settings.get("theme", {}))
        color_fields: dict[str, QLineEdit] = {}
        theme_box = QGroupBox("Colors")
        theme_form = QFormLayout(theme_box)
        preset_row = QHBoxLayout()
        preset_combo = QComboBox()
        preset_combo.addItems(sorted(self.settings.get("theme_presets", {}).keys()))
        preset_name = QLineEdit("")
        preset_name.setPlaceholderText("Preset name")
        preset_row.addWidget(preset_combo, 1)
        preset_row.addWidget(preset_name, 1)
        theme_form.addRow("Theme preset", preset_row)
        swatches: dict[str, QPushButton] = {}
        progress_values = {"enabled": False, "start": theme_values["accent"], "end": theme_values["accent"]}
        progress_values.update(self.settings.get("progress_gradient", {}))
        progress_box = QGroupBox("Progress Bar")
        progress_form = QFormLayout(progress_box)
        progress_gradient_enabled = QCheckBox("Use gradient fill")
        progress_gradient_enabled.setChecked(bool(progress_values.get("enabled")))
        progress_color_fields: dict[str, QLineEdit] = {}
        progress_swatches: dict[str, QPushButton] = {}

        def current_theme_from_fields() -> dict[str, str]:
            return {key: field.text().strip() for key, field in color_fields.items()}

        def current_progress_from_fields() -> dict[str, Any]:
            return {
                "enabled": progress_gradient_enabled.isChecked(),
                "start": progress_color_fields["start"].text().strip(),
                "end": progress_color_fields["end"].text().strip(),
            }

        def unique_custom_roots_from_text() -> list[str]:
            unique: list[str] = []
            seen = {normalized_path_key(DEFAULT_DATASETS_DIR)}
            duplicates: list[str] = []
            for line in roots.toPlainText().splitlines():
                text = line.strip()
                if not text:
                    continue
                key = normalized_path_key(Path(text))
                if key in seen:
                    duplicates.append(text)
                    continue
                seen.add(key)
                unique.append(text)
            if duplicates:
                QMessageBox.information(dialog, APP_NAME, "Duplicate project roots were ignored:\n\n" + "\n".join(duplicates))
            return unique

        def update_swatch(key: str) -> None:
            value = color_fields[key].text().strip()
            color = QColor(value)
            swatch = swatches[key]
            shown = color.name() if color.isValid() else "#000000"
            swatch.setStyleSheet(f"QPushButton {{ background: {shown}; border: 1px solid #666; border-radius: 4px; min-width: 34px; max-width: 34px; min-height: 22px; max-height: 22px; padding: 0; }}")

        def apply_theme_from_fields() -> None:
            self.apply_theme_values(current_theme_from_fields())

        def apply_progress_from_fields() -> None:
            self.settings["progress_gradient"] = current_progress_from_fields()
            save_settings(self.settings)
            self.apply_theme()

        for key in THEME:
            field = QLineEdit(theme_values.get(key, THEME[key]))
            color_fields[key] = field
            swatch = QPushButton("")
            swatches[key] = swatch
            swatch.setToolTip(f"Pick {key} color")
            swatch.setCursor(Qt.PointingHandCursor)
            color_row = QHBoxLayout()
            color_row.setContentsMargins(0, 0, 0, 0)
            color_row.addWidget(field, 1)
            color_row.addWidget(swatch)
            color_widget = QWidget()
            color_widget.setLayout(color_row)

            def choose_color(target_key: str = key) -> None:
                current = QColor(color_fields[target_key].text().strip())
                color = QColorDialog.getColor(current if current.isValid() else QColor(THEME[target_key]), dialog, f"Choose {target_key} color")
                if color.isValid():
                    color_fields[target_key].setText(color.name())
                    update_swatch(target_key)
                    apply_theme_from_fields()

            swatch.clicked.connect(lambda _checked=False, target_key=key: choose_color(target_key))
            field.textChanged.connect(lambda _text, target_key=key: update_swatch(target_key))
            field.editingFinished.connect(apply_theme_from_fields)
            update_swatch(key)
            theme_form.addRow(key, add_help(color_widget, f"Hex color for theme key '{key}'. Use the swatch to choose visually."))

        def update_progress_swatch(key: str) -> None:
            value = progress_color_fields[key].text().strip()
            color = QColor(value)
            shown = color.name() if color.isValid() else "#000000"
            progress_swatches[key].setStyleSheet(f"QPushButton {{ background: {shown}; border: 1px solid #666; border-radius: 4px; min-width: 34px; max-width: 34px; min-height: 22px; max-height: 22px; padding: 0; }}")

        for key, label in [("start", "Gradient start"), ("end", "Gradient end")]:
            field = QLineEdit(str(progress_values.get(key, theme_values["accent"])))
            progress_color_fields[key] = field
            swatch = QPushButton("")
            progress_swatches[key] = swatch
            swatch.setToolTip(f"Pick progress {key} color")
            swatch.setCursor(Qt.PointingHandCursor)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(field, 1)
            row.addWidget(swatch)
            widget = QWidget()
            widget.setLayout(row)

            def choose_progress_color(target_key: str = key) -> None:
                current = QColor(progress_color_fields[target_key].text().strip())
                color = QColorDialog.getColor(current if current.isValid() else QColor(theme_values["accent"]), dialog, f"Choose progress {target_key} color")
                if color.isValid():
                    progress_color_fields[target_key].setText(color.name())
                    update_progress_swatch(target_key)
                    apply_progress_from_fields()

            swatch.clicked.connect(lambda _checked=False, target_key=key: choose_progress_color(target_key))
            field.textChanged.connect(lambda _text, target_key=key: update_progress_swatch(target_key))
            field.editingFinished.connect(apply_progress_from_fields)
            update_progress_swatch(key)
            progress_form.addRow(label, add_help(widget, "Progress bar gradient color. This is stored separately from the main UI theme colors."))
        progress_gradient_enabled.stateChanged.connect(apply_progress_from_fields)
        progress_form.addRow(add_help(progress_gradient_enabled, "When off, progress bars use the current accent color."))
        theme_actions = QHBoxLayout()
        save_preset = QPushButton("Save Preset")
        load_preset = QPushButton("Load Preset")
        remove_preset = QPushButton("Remove Preset")
        select_preset = QPushButton("Select Preset")
        reset_colors = QPushButton("Reset Built-in")
        windows_theme = QPushButton("Use Windows Theme")
        for button in [save_preset, load_preset, remove_preset, select_preset, reset_colors, windows_theme]:
            theme_actions.addWidget(button)
        theme_form.addRow(theme_actions)

        def refresh_preset_combo(selected: str = "") -> None:
            preset_combo.blockSignals(True)
            preset_combo.clear()
            names = sorted(self.settings.get("theme_presets", {}).keys())
            preset_combo.addItems(names)
            if selected and selected in names:
                preset_combo.setCurrentText(selected)
            preset_combo.blockSignals(False)

        def load_preset_fields() -> None:
            name = preset_combo.currentText()
            preset = self.settings.get("theme_presets", {}).get(name)
            if not preset:
                return
            for key, value in {**THEME, **preset}.items():
                if key in color_fields:
                    color_fields[key].setText(value)
            preset_name.setText(name)

        def save_preset_fields() -> None:
            name = preset_name.text().strip() or preset_combo.currentText().strip()
            if not name:
                QMessageBox.information(dialog, APP_NAME, "Enter a preset name first.")
                return
            self.save_theme_preset(name, current_theme_from_fields())
            refresh_preset_combo(name)

        def remove_preset_fields() -> None:
            name = preset_combo.currentText()
            if not name:
                return
            self.settings.get("theme_presets", {}).pop(name, None)
            if self.settings.get("selected_theme_preset") == name:
                self.settings.pop("selected_theme_preset", None)
            save_settings(self.settings)
            refresh_preset_combo()

        def select_preset_fields() -> None:
            name = preset_combo.currentText()
            if not name:
                return
            load_preset_fields()
            self.settings["selected_theme_preset"] = name
            self.apply_theme_values(current_theme_from_fields())

        def preset_combo_selected(_name: str) -> None:
            select_preset_fields()

        def reset_color_fields() -> None:
            for key, value in THEME.items():
                color_fields[key].setText(value)

        def use_windows_theme() -> None:
            preset = windows_theme_preset()
            for key, value in preset.items():
                if key in color_fields:
                    color_fields[key].setText(value)
            self.settings.setdefault("theme_presets", {})["Windows Current"] = preset
            self.settings["selected_theme_preset"] = "Windows Current"
            self.apply_theme_values(current_theme_from_fields())
            refresh_preset_combo("Windows Current")

        save_preset.clicked.connect(save_preset_fields)
        load_preset.clicked.connect(load_preset_fields)
        remove_preset.clicked.connect(remove_preset_fields)
        select_preset.clicked.connect(select_preset_fields)
        reset_colors.clicked.connect(reset_color_fields)
        windows_theme.clicked.connect(use_windows_theme)
        preset_combo.currentTextChanged.connect(preset_combo_selected)
        layout.addRow("Ostris Toolkit Path", add_help(toolkit, "Used only for scanning installed config/examples and preset metadata."))
        layout.addRow("Caption model locations", add_help(model_locations, "One local caption-model folder per line. The first path becomes the default Model path in Caption Settings."))
        layout.addRow("Hugging Face API key", add_help(hf_key, "Optional token for gated/private Hugging Face model downloads or API captioning. Stored locally."))
        layout.addRow("Civitai API key", add_help(civitai_key, "Optional token for Civitai downloads that require authentication. Stored locally."))
        layout.addRow("OpenAI API key", add_help(openai_key, "Optional key for API-model captioning. Images may be sent to the selected provider."))
        layout.addRow("Gemini API key", add_help(gemini_key, "Optional key for API-model captioning. Images may be sent to the selected provider."))
        layout.addRow("Anthropic API key", add_help(anthropic_key, "Optional key for API-model captioning. Images may be sent to the selected provider."))
        layout.addRow("Custom provider name", add_help(custom_name, "Label for another provider, endpoint, or gateway."))
        layout.addRow("Custom provider URL", add_help(custom_url, "HTTP endpoint for Custom HTTP captioning. The app POSTs image_base64, image path, trigger, and prompt as JSON."))
        layout.addRow("Custom provider key", add_help(custom_key, "Optional token for a custom HTTP caption provider or model host."))
        layout.addRow("Custom project roots", add_help(roots, "One user-added project library scan root per line."))
        layout.addRow(theme_box)
        layout.addRow(progress_box)
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addRow(buttons)
        save.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec():
            self.settings["ostris_toolkit_path"] = toolkit.text().strip()
            self.settings["caption_model_locations"] = [line.strip() for line in model_locations.toPlainText().splitlines() if line.strip()]
            self.settings["provider_api_keys"] = {
                "huggingface": hf_key.text().strip(),
                "civitai": civitai_key.text().strip(),
                "openai": openai_key.text().strip(),
                "gemini": gemini_key.text().strip(),
                "anthropic": anthropic_key.text().strip(),
                "custom": custom_key.text().strip(),
            }
            self.settings["custom_api_provider_name"] = custom_name.text().strip() or "Custom HTTP"
            self.settings["custom_api_url"] = custom_url.text().strip()
            self.settings.pop("api_key", None)
            self.settings["custom_dataset_roots"] = unique_custom_roots_from_text()
            self.settings["theme"] = current_theme_from_fields()
            self.settings["progress_gradient"] = current_progress_from_fields()
            if not self.settings.get("model_path") and self.settings["caption_model_locations"]:
                self.settings["model_path"] = self.settings["caption_model_locations"][0]
            save_settings(self.settings)
            self.apply_theme()
            self.refresh_library()
            self.refresh_project_combo()

    def update_ostris_job_type_layout(self) -> None:
        is_slider = self.combo_data(self.job_type) == "concept_slider"
        self.slider_card.setVisible(is_slider)
        self.target_card.setVisible(not is_slider)
        self.config_trigger.setEnabled(not is_slider)
        if is_slider:
            self.config_trigger.setText("")
        self.form_to_yaml()

    def add_blank_sample_prompt(self) -> None:
        self.add_sample_prompt_row({"prompt": ""})
        self.form_to_yaml()

    def clear_sample_prompt_rows(self) -> None:
        for row in self.sample_rows:
            widget = row.get("widget")
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.sample_rows = []

    def add_sample_prompt_row(self, sample: dict[str, Any]) -> None:
        box = QGroupBox(f"Prompt {len(self.sample_rows) + 1}")
        layout = QGridLayout(box)
        prompt = QLineEdit(str(sample.get("prompt", "")))
        width = QLineEdit(str(sample.get("width", "")))
        height = QLineEdit(str(sample.get("height", "")))
        seed = QLineEdit(str(sample.get("seed", "")))
        scale = QLineEdit(str(sample.get("network_multiplier", "")))
        remove = QPushButton("Remove")
        row_data: dict[str, QWidget] = {
            "widget": box,
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "network_multiplier": scale,
            "remove": remove,
        }
        remove.clicked.connect(lambda: self.remove_sample_prompt_row(row_data))
        for editor in [prompt, width, height, seed, scale]:
            editor.textChanged.connect(self.form_to_yaml)
        layout.addWidget(QLabel("Prompt"), 0, 0)
        layout.addWidget(add_help(prompt, "Ostris sample prompt. The trigger word is not inserted automatically by AI Toolkit."), 0, 1, 1, 7)
        layout.addWidget(QLabel("Width"), 1, 0)
        layout.addWidget(add_help(width, "Optional per-prompt width. Blank uses Sample width."), 1, 1)
        layout.addWidget(QLabel("Height"), 1, 2)
        layout.addWidget(add_help(height, "Optional per-prompt height. Blank uses Sample height."), 1, 3)
        layout.addWidget(QLabel("Seed"), 1, 4)
        layout.addWidget(add_help(seed, "Optional per-prompt seed. Blank uses Sample seed."), 1, 5)
        layout.addWidget(QLabel("LoRA Scale"), 1, 6)
        layout.addWidget(add_help(scale, "Optional per-prompt network_multiplier / LoRA Scale."), 1, 7)
        layout.addWidget(add_help(remove, "Remove this sample prompt row."), 0, 8, 2, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(5, 1)
        layout.setColumnStretch(7, 1)
        self.sample_rows.append(row_data)
        self.sample_rows_layout.addWidget(box)
        self.refresh_sample_prompt_titles()

    def remove_sample_prompt_row(self, row_data: dict[str, QWidget]) -> None:
        if len(self.sample_rows) <= 1:
            cast_prompt = row_data["prompt"]
            if isinstance(cast_prompt, QLineEdit):
                cast_prompt.clear()
            return
        if row_data in self.sample_rows:
            self.sample_rows.remove(row_data)
        widget = row_data.get("widget")
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        self.refresh_sample_prompt_titles()
        self.form_to_yaml()

    def refresh_sample_prompt_titles(self) -> None:
        for index, row in enumerate(self.sample_rows, start=1):
            widget = row.get("widget")
            if isinstance(widget, QGroupBox):
                widget.setTitle(f"Prompt {index}")

    def sample_prompt_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in self.sample_rows:
            prompt_widget = row.get("prompt")
            if not isinstance(prompt_widget, QLineEdit):
                continue
            prompt = prompt_widget.text().strip()
            if not prompt:
                continue
            record: dict[str, Any] = {"prompt": prompt}
            for key in ["width", "height", "seed"]:
                widget = row.get(key)
                if isinstance(widget, QLineEdit) and widget.text().strip().isdigit():
                    record[key] = int(widget.text().strip())
            scale = row.get("network_multiplier")
            if isinstance(scale, QLineEdit) and scale.text().strip():
                record["network_multiplier"] = scale.text().strip()
            records.append(record)
        return records

    def sample_prompt_lines(self) -> list[str]:
        return [record["prompt"] for record in self.sample_prompt_records()]

    def set_sample_prompt_records(self, samples: list[dict[str, Any]]) -> None:
        self.clear_sample_prompt_rows()
        for sample in samples or [{"prompt": ""}]:
            self.add_sample_prompt_row(sample)
        self.refresh_sample_prompt_titles()

    def parse_ostris_resolutions(self) -> list[int]:
        values: list[int] = []
        for part in self.resolution.text().replace("x", ",").split(","):
            part = part.strip()
            if part.isdigit():
                values.append(int(part))
        return values or [512, 768, 1024]

    def apply_ostris_arch_defaults(self) -> None:
        if self.syncing_yaml:
            return
        arch = ostris_arch_by_value(str(self.model_arch.currentData() or "zimage:turbo"))
        self.syncing_yaml = True
        try:
            self.model_name_or_path.setText(arch.get("name_or_path", ""))
            self.training_adapter_path.setText(arch.get("assistant_lora_path", ""))
            self.extras_name_or_path.setText(arch.get("extras_name_or_path", ""))
            self.low_vram.setChecked(bool(arch.get("low_vram", False)))
            self.match_target_res.setChecked(bool(arch.get("match_target_res", False)))
            qtype = arch.get("qtype", "qfloat8")
            self.quantize_transformer.setCurrentIndex(max(0, self.quantize_transformer.findData(qtype)))
            self.quantize_text_encoder.setCurrentIndex(max(0, self.quantize_text_encoder.findData(qtype)))
            self.sample_steps.setValue(int(arch.get("sample_steps", self.sample_steps.value())))
            self.guidance_scale.setText(str(arch.get("guidance_scale", self.guidance_scale.text())))
        finally:
            self.syncing_yaml = False
        self.form_to_yaml()

    def combo_data(self, combo: QComboBox) -> str:
        data = combo.currentData()
        return str(data) if data is not None else combo.currentText()

    def config_dict(self) -> dict[str, Any]:
        samples = self.sample_prompt_records()
        model_kwargs: dict[str, Any] = {}
        if self.match_target_res.isChecked():
            model_kwargs["match_target_res"] = True
        if self.kv_cache.isChecked():
            model_kwargs["kv_cache"] = True
        model: dict[str, Any] = {
            "name_or_path": self.model_name_or_path.text().strip() or None,
            "arch": self.combo_data(self.model_arch),
            "low_vram": self.low_vram.isChecked(),
            "quantize": bool(self.combo_data(self.quantize_transformer)),
            "qtype": self.combo_data(self.quantize_transformer) or "qfloat8",
            "quantize_te": bool(self.combo_data(self.quantize_text_encoder)),
            "qtype_te": self.combo_data(self.quantize_text_encoder) or "qfloat8",
            "model_kwargs": model_kwargs,
            "compile": self.compile_model.isChecked(),
        }
        if self.training_adapter_path.text().strip():
            model["assistant_lora_path"] = self.training_adapter_path.text().strip()
        if self.extras_name_or_path.text().strip():
            model["extras_name_or_path"] = self.extras_name_or_path.text().strip()
        if self.layer_offloading.isChecked():
            model["layer_offloading"] = True

        network: dict[str, Any] = {
            "type": self.combo_data(self.network_type),
            "linear": self.rank.value(),
            "linear_alpha": self.alpha.value(),
            "network_kwargs": {"ignore_if_contains": []},
        }
        if self.conv_rank.value() > 0:
            network["conv"] = self.conv_rank.value()
            network["conv_alpha"] = self.conv_rank.value()
        if self.combo_data(self.network_type) == "lokr":
            network["lokr_full_rank"] = True
            network["lokr_factor"] = int(self.combo_data(self.lokr_factor))

        caption_ext = self.caption_extension.currentText().strip().lstrip(".") or "txt"
        process: dict[str, Any] = {
            "type": self.combo_data(self.job_type),
            "training_folder": self.train_folder.text(),
            "device": self.device.currentText(),
            "trigger_word": None if self.combo_data(self.job_type) == "concept_slider" else (self.config_trigger.text().strip() or None),
            "performance_log_every": 10,
            "network": network,
            "save": {
                "dtype": self.dtype.currentText(),
                "save_every": self.save_every.value(),
                "max_step_saves_to_keep": self.max_checkpoints.value(),
                "save_format": "diffusers",
                "push_to_hub": False,
            },
            "datasets": [
                {
                    "folder_path": self.dataset_folder.text(),
                    "mask_path": None,
                    "mask_min_value": 0.1,
                    "default_caption": "",
                    "caption_ext": caption_ext,
                    "caption_dropout_rate": float(self.caption_dropout.text() or 0),
                    "cache_latents_to_disk": self.cache_latents.isChecked(),
                    "is_reg": self.is_regularization.isChecked(),
                    "network_weight": float(self.network_weight.text() or 1),
                    "resolution": self.parse_ostris_resolutions(),
                    "controls": [],
                    "shrink_video_to_frames": True,
                    "num_frames": 1,
                    "flip_x": False,
                    "flip_y": False,
                    "num_repeats": self.num_repeats.value(),
                }
            ],
            "train": {
                "batch_size": self.batch_size.value(),
                "bypass_guidance_embedding": True,
                "steps": self.steps.value(),
                "gradient_accumulation": self.gradient_accumulation.value(),
                "train_unet": True,
                "train_text_encoder": False,
                "gradient_checkpointing": self.gradient_checkpointing.isChecked(),
                "noise_scheduler": "flowmatch",
                "optimizer": self.optimizer.text(),
                "timestep_type": self.timestep_type.currentText(),
                "content_or_style": "balanced",
                "optimizer_params": {"weight_decay": float(self.weight_decay.text() or 0)},
                "unload_text_encoder": self.unload_te.isChecked(),
                "cache_text_embeddings": self.cache_text_embeddings.isChecked(),
                "lr": float(self.lr.text() or 0),
                "ema_config": {"use_ema": False, "ema_decay": 0.99},
                "skip_first_sample": False,
                "force_first_sample": self.force_first_sample.isChecked(),
                "disable_sampling": self.disable_sampling.isChecked(),
                "dtype": self.dtype.currentText(),
                "diff_output_preservation": False,
                "diff_output_preservation_multiplier": 1.0,
                "diff_output_preservation_class": "person",
                "switch_boundary_every": 1,
                "loss_type": self.loss_type.currentText(),
            },
            "logging": {"log_every": 1, "use_ui_logger": True},
            "model": model,
            "sample": {
                "sample_every": self.sample_every.value(),
                "sample_start_step": self.sample_start_step.value(),
                "sampler": self.sample_sampler.currentText(),
                "guidance_scale": float(self.guidance_scale.text() or 0),
                "sample_steps": self.sample_steps.value(),
                "width": self.sample_width.value(),
                "height": self.sample_height.value(),
                "seed": self.sample_seed.value(),
                "walk_seed": self.walk_seed.isChecked(),
                "samples": samples,
            },
        }
        if self.combo_data(self.job_type) == "concept_slider":
            process["slider"] = {
                "guidance_strength": 3.0,
                "anchor_strength": 1.0,
                "positive_prompt": self.slider_positive_prompt.text(),
                "negative_prompt": self.slider_negative_prompt.text(),
                "target_class": self.slider_target_class.text(),
                "anchor_class": self.slider_anchor_class.text(),
            }
        return {
            "job": "extension",
            "config": {
                "name": self.job_name.text(),
                "process": [process],
            },
            "meta": {"name": "[name]", "version": "1.0", "source": APP_NAME},
        }

    def form_to_yaml(self) -> None:
        if self.syncing_yaml:
            return
        self.syncing_yaml = True
        try:
            vbar = self.yaml_editor.verticalScrollBar()
            hbar = self.yaml_editor.horizontalScrollBar()
            old_v = vbar.value()
            old_h = hbar.value()
            cursor_position = self.yaml_editor.textCursor().position()
            text = yaml.safe_dump(self.config_dict(), sort_keys=False) if yaml else json.dumps(self.config_dict(), indent=2)
            self.yaml_editor.setPlainText(text)
            cursor = self.yaml_editor.textCursor()
            cursor.setPosition(min(cursor_position, len(text)))
            self.yaml_editor.setTextCursor(cursor)
            vbar.setValue(min(old_v, vbar.maximum()))
            hbar.setValue(min(old_h, hbar.maximum()))
            self.yaml_status.setText(f"Export size: {self.export_size_text() if hasattr(self, 'export_size') else 'unknown'} | Config resolution: {self.resolution.text()}")
        finally:
            self.syncing_yaml = False

    def yaml_text_changed(self) -> None:
        if self.syncing_yaml:
            return
        self.validate_yaml(update_form=True, quiet=True)

    def new_ostris_yaml(self) -> None:
        if hasattr(self, "dataset_folder"):
            fallback_folder = str(self.project_folder("export")) if self.dataset_root else ""
            self.dataset_folder.setText(str(self.manifest.data.get("export", {}).get("folder") or fallback_folder))
            self.config_trigger.setText(self.trigger_edit.text().strip() if hasattr(self, "trigger_edit") else "")
            size = self.export_size_text() if hasattr(self, "export_size") else "1024x1024"
            if size != "Original":
                export_res = parse_size(size)[0]
                self.resolution.setText(f"512, 768, {export_res}")
                self.sample_width.setValue(export_res)
                self.sample_height.setValue(parse_size(size)[1])
        self.form_to_yaml()

    def validate_yaml(self, update_form: bool = False, quiet: bool = False) -> None:
        text = self.yaml_editor.toPlainText()
        try:
            data = yaml.safe_load(text) if yaml else json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("YAML root must be a mapping.")
            process = data.get("config", {}).get("process", [{}])[0]
            missing = []
            for key in ["training_folder", "datasets", "train", "network", "save"]:
                if key not in process:
                    missing.append(key)
            self.yaml_status.setText("YAML valid" + (f" | Missing common fields: {', '.join(missing)}" if missing else ""))
            if update_form:
                self.yaml_to_form(data)
            if not quiet:
                QMessageBox.information(self, APP_NAME, self.yaml_status.text())
        except Exception as exc:
            self.yaml_status.setText(f"YAML parse error: {exc}")
            if not quiet:
                QMessageBox.warning(self, APP_NAME, self.yaml_status.text())

    def yaml_to_form(self, data: dict[str, Any]) -> None:
        try:
            process = data.get("config", {}).get("process", [{}])[0]
            dataset = process.get("datasets", [{}])[0]
            train = process.get("train", {})
            network = process.get("network", {})
            save = process.get("save", {})
            sample = process.get("sample", {})
            model = process.get("model", {})
        except Exception:
            return
        self.syncing_yaml = True
        try:
            self.job_name.setText(str(data.get("config", {}).get("name", self.job_name.text())))
            process_type = str(process.get("type", self.combo_data(self.job_type)))
            idx = self.job_type.findData(process_type)
            if idx >= 0:
                self.job_type.setCurrentIndex(idx)
            slider = process.get("slider", {})
            if isinstance(slider, dict):
                self.slider_target_class.setText(str(slider.get("target_class", self.slider_target_class.text())))
                self.slider_positive_prompt.setText(str(slider.get("positive_prompt", self.slider_positive_prompt.text())))
                self.slider_negative_prompt.setText(str(slider.get("negative_prompt", self.slider_negative_prompt.text())))
                self.slider_anchor_class.setText(str(slider.get("anchor_class", self.slider_anchor_class.text())))
            self.train_folder.setText(str(process.get("training_folder", self.train_folder.text())))
            self.device.setCurrentText(str(process.get("device", self.device.currentText())))
            self.dataset_folder.setText(str(dataset.get("folder_path", self.dataset_folder.text())))
            self.config_trigger.setText(str(process.get("trigger_word") or self.config_trigger.text()))
            self.caption_extension.setCurrentText(str(dataset.get("caption_ext", self.caption_extension.currentText())))
            self.caption_dropout.setText(str(dataset.get("caption_dropout_rate", self.caption_dropout.text())))
            self.network_weight.setText(str(dataset.get("network_weight", self.network_weight.text())))
            if dataset.get("resolution") is not None:
                res = dataset.get("resolution")
                self.resolution.setText(", ".join(str(x) for x in res) if isinstance(res, list) else str(res))
            self.cache_latents.setChecked(bool(dataset.get("cache_latents_to_disk", False)))
            self.is_regularization.setChecked(bool(dataset.get("is_reg", False)))
            self.lr.setText(str(train.get("lr", self.lr.text())))
            self.optimizer.setText(str(train.get("optimizer", self.optimizer.text())))
            if train.get("optimizer_params", {}).get("weight_decay") is not None:
                self.weight_decay.setText(str(train["optimizer_params"]["weight_decay"]))
            self.timestep_type.setCurrentText(str(train.get("timestep_type", self.timestep_type.currentText())))
            self.loss_type.setCurrentText(str(train.get("loss_type", self.loss_type.currentText())))
            self.unload_te.setChecked(bool(train.get("unload_text_encoder", False)))
            self.cache_text_embeddings.setChecked(bool(train.get("cache_text_embeddings", False)))
            self.gradient_checkpointing.setChecked(bool(train.get("gradient_checkpointing", True)))
            self.force_first_sample.setChecked(bool(train.get("force_first_sample", False)))
            self.disable_sampling.setChecked(bool(train.get("disable_sampling", False)))
            idx = self.network_type.findData(str(network.get("type", self.combo_data(self.network_type))))
            if idx >= 0:
                self.network_type.setCurrentIndex(idx)
            if network.get("lokr_factor") is not None:
                idx = self.lokr_factor.findData(str(network.get("lokr_factor")))
                if idx >= 0:
                    self.lokr_factor.setCurrentIndex(idx)
            for widget, value in [
                (self.batch_size, train.get("batch_size")),
                (self.gradient_accumulation, train.get("gradient_accumulation")),
                (self.steps, train.get("steps")),
                (self.save_every, save.get("save_every")),
                (self.max_checkpoints, save.get("max_step_saves_to_keep")),
                (self.rank, network.get("linear")),
                (self.alpha, network.get("linear_alpha")),
                (self.conv_rank, network.get("conv")),
                (self.num_repeats, dataset.get("num_repeats")),
                (self.sample_every, sample.get("sample_every")),
                (self.sample_start_step, sample.get("sample_start_step")),
                (self.sample_steps, sample.get("sample_steps")),
                (self.sample_width, sample.get("width")),
                (self.sample_height, sample.get("height")),
                (self.sample_seed, sample.get("seed")),
            ]:
                if value is not None:
                    widget.setValue(int(value))
            self.dtype.setCurrentText(str(save.get("dtype", train.get("dtype", self.dtype.currentText()))))
            arch = str(model.get("arch", self.combo_data(self.model_arch)))
            idx = self.model_arch.findData(arch)
            if idx >= 0:
                self.model_arch.setCurrentIndex(idx)
            self.model_name_or_path.setText(str(model.get("name_or_path", self.model_name_or_path.text()) or ""))
            self.training_adapter_path.setText(str(model.get("assistant_lora_path", self.training_adapter_path.text()) or ""))
            self.extras_name_or_path.setText(str(model.get("extras_name_or_path", self.extras_name_or_path.text()) or ""))
            self.low_vram.setChecked(bool(model.get("low_vram", False)))
            self.layer_offloading.setChecked(bool(model.get("layer_offloading", False)))
            self.match_target_res.setChecked(bool(model.get("model_kwargs", {}).get("match_target_res", False)))
            self.kv_cache.setChecked(bool(model.get("model_kwargs", {}).get("kv_cache", False)))
            self.compile_model.setChecked(bool(model.get("compile", False)))
            for combo, enabled_key, qtype_key in [(self.quantize_transformer, "quantize", "qtype"), (self.quantize_text_encoder, "quantize_te", "qtype_te")]:
                qtype = str(model.get(qtype_key, "qfloat8")) if model.get(enabled_key, False) else ""
                idx = combo.findData(qtype)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.sample_sampler.setCurrentText(str(sample.get("sampler", self.sample_sampler.currentText())))
            self.guidance_scale.setText(str(sample.get("guidance_scale", self.guidance_scale.text())))
            self.walk_seed.setChecked(bool(sample.get("walk_seed", False)))
            prompts = sample.get("samples", sample.get("prompts", []))
            if isinstance(prompts, list):
                records = [item if isinstance(item, dict) else {"prompt": str(item)} for item in prompts]
                self.set_sample_prompt_records(records)
        finally:
            self.syncing_yaml = False
        self.update_ostris_job_type_layout()

    def import_yaml(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Import YAML config", str(Path.home()), "YAML (*.yaml *.yml)")
        if file:
            self.yaml_editor.setPlainText(Path(file).read_text(encoding="utf-8", errors="replace"))
            self.validate_yaml(update_form=True)

    def export_yaml(self) -> None:
        default_folder = self.dataset_root if self.dataset_root else APP_DIR
        file, _ = QFileDialog.getSaveFileName(self, "Export AI Toolkit YAML", str(default_folder / f"{self.job_name.text()}.yaml"), "YAML (*.yaml *.yml)")
        if file:
            Path(file).write_text(self.yaml_editor.toPlainText(), encoding="utf-8")
            self.manifest.data.setdefault("ostris_configs", []).append({"path": file, "time": timestamp(), "provenance": "User preset"})
            self.manifest.save("ostris yaml exported")

    def scan_toolkit_examples(self) -> None:
        root = Path(self.settings.get("ostris_toolkit_path", ""))
        examples = root / "config" / "examples"
        if not examples.exists():
            QMessageBox.information(self, APP_NAME, "Set Settings -> Ostris Toolkit Path to scan config/examples.")
            return
        files = list(examples.rglob("*.yml")) + list(examples.rglob("*.yaml"))
        QMessageBox.information(self, APP_NAME, f"Found {len(files)} example config(s).\nImport one with Import YAML.")

    def insert_trigger_in_samples(self) -> None:
        trigger = self.config_trigger.text().strip()
        if not self.sample_rows:
            self.add_sample_prompt_row({"prompt": f"{trigger}, "})
            return
        target_row = self.sample_rows[-1]
        prompt_widget = target_row.get("prompt")
        if isinstance(prompt_widget, QLineEdit):
            existing = prompt_widget.text().strip()
            prompt_widget.setText(f"{trigger}, {existing}" if existing and trigger not in existing else f"{trigger}, ")

    def samples_from_captions(self) -> None:
        root = self.require_dataset_root()
        if root is None:
            return
        captions = []
        for cap in self.current_prepped_folder(root).glob(f"*{CAPTION_EXT}"):
            text = cap.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                captions.append(text)
        self.set_sample_prompt_records([{"prompt": caption} for caption in captions[:20]] or [{"prompt": ""}])
        self.form_to_yaml()

    def import_samples(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Import sample prompts", str(Path.home()), "Text (*.txt)")
        if file:
            lines = [line.strip() for line in Path(file).read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
            self.set_sample_prompt_records([{"prompt": line} for line in lines] or [{"prompt": ""}])
            self.form_to_yaml()

    def export_samples(self) -> None:
        default_folder = self.dataset_root if self.dataset_root else APP_DIR
        file, _ = QFileDialog.getSaveFileName(self, "Export sample prompts", str(default_folder / "sample_prompts.txt"), "Text (*.txt)")
        if file:
            Path(file).write_text("\n".join(self.sample_prompt_lines()), encoding="utf-8")

    def validate_sample_triggers(self) -> None:
        trigger = self.config_trigger.text().strip()
        missing = [str(i + 1) for i, line in enumerate(self.sample_prompt_lines()) if line.strip() and trigger and trigger not in line]
        QMessageBox.information(self, APP_NAME, f"Prompts missing trigger: {', '.join(missing) or 'none'}")


def main() -> int:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PrepMI.PrepYU")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
