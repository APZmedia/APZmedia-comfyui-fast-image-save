# APZmedia Fast Image Save

Saves images faster than ComfyUI's default Save Image node. That's the pitch. It uses OpenCV directly, skips the workflow embedding, and doesn't apologize for either of those choices.

**Important: workflow data is not saved in the images.** If you need that, use the standard node. If you need speed, use this one.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pabloapz)

---

## Overview

The built-in Save Image node embeds the workflow JSON into every PNG it produces. That's useful for reproducibility and largely irrelevant if you're saving a 10,000-frame image sequence where disk throughput needs to keep up with generation. This node skips that step.

---

## Features

- **PNG, JPEG, and WebP output**
- **Multi-backend support** — auto-selects fastest library per format
- **Parallel saving** — multi-threaded I/O for maximum throughput
- **Batch filename generation** — eliminates O(n²) collision checks
- **Optimized tensor operations** — minimal CPU-GPU transfer overhead
- **Compression control** — turn it off for maximum speed
- **Memory efficient** — no image duplication in output
- Suitable for high-volume batch and sequence output

---

## Performance Optimizations

### Multi-Backend Support
The node automatically selects the fastest available library for each format:

| Format | Fastest | Quality | Notes |
|--------|---------|---------|-------|
| PNG | OpenCV | Good | Fastest general use |
| JPEG | **TurboJPEG** 🚀 | Excellent | 2-3x faster than OpenCV |
| WebP | PIL / webp-native | Best | Best quality control |

Optional Python packages (`PyTurboJPEG`, `webp`) are **auto-installed on first load** — no manual steps needed there. Note that `PyTurboJPEG` is just a wrapper: it also needs the native `libturbojpeg` library installed on your system (see [TurboJPEG setup](#turbojpeg-setup) below). If that native library isn't found, the node quietly falls back to OpenCV/PIL for JPEG — it won't crash or block other formats.

### Parallel Saving
Enable `parallel_save` to save multiple images concurrently. Uses a thread pool optimized for I/O-bound operations. Tune `max_workers` (1-16) based on your storage:
- **SSD/NVMe**: 4-8 workers
- **HDD**: 2-4 workers
- **Network storage**: 1-2 workers

### Batch Filename Collision Detection
Instead of checking each file individually (O(n²)), the node batches directory listings and uses set-based lookups.

### Tensor Optimization
- Minimal CPU-GPU transfers
- Contiguous memory layouts for faster conversion
- Batched processing where possible

---

## Node Inputs

| Input | Description |
|-------|-------------|
| `images` | Image batch to save |
| `output_path` | Directory path (supports `[time(%Y-%m-%d)]` formatting) |
| `filename_prefix` | Base name for files |
| `filename_delimiter` | Separator between prefix and number |
| `filename_number_padding` | Zero-padding for numbers (1-10) |
| `filename_number_start` | Start numbering at 0 or 1 |
| `extension` | png / jpeg / webp |
| `dpi` | DPI metadata (1-600) |
| `quality` | JPEG/WebP quality 1-100 |
| `optimize_image` | Compression optimization (png/jpeg/webp) |
| `lossless_webp` | Lossless WebP mode |
| `overwrite_mode` | Overwrite existing files |
| `show_previews` | Print save location to console |
| `parallel_save` | Enable multi-threaded saving |
| `max_workers` | Thread pool size (1-16) |
| `backend` | auto / opencv / pil / turbojpeg / webp-native |

### Backend Options
- **auto**: Automatically selects fastest available (recommended)
- **opencv**: Always available, good general performance
- **pil**: Best quality, more format options
- **turbojpeg**: Fastest JPEG (requires the native library — see [TurboJPEG setup](#turbojpeg-setup))
- **webp-native**: Native WebP library (auto-installed if available)

---

## Installation

1. Clone this repo into your ComfyUI `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/APZmedia/APZmedia-comfyui-fast-image-save.git
   ```
2. Restart ComfyUI — optional performance libraries will auto-install on first load
3. Find the node under the **APZmedia Fast image save** category

**That's it!** PyTurboJPEG and webp libraries are automatically installed if not present. For the JPEG speed boost, also install the native TurboJPEG library below.

---

## TurboJPEG Setup

`PyTurboJPEG` (the Python package) is only a wrapper around the native `libturbojpeg` library, which pip cannot install for you. Without it, PyTurboJPEG raises `"Unable to locate turbojpeg library automatically"` — this node catches that and silently falls back to OpenCV, so it's safe to ignore if you don't need the extra JPEG speed. To enable it:

- **Windows**: Install the [libjpeg-turbo](https://github.com/libjpeg-turbo/libjpeg-turbo/releases) SDK (the `-vc64.exe` installer). PyTurboJPEG looks for it at the default install path `C:\libjpeg-turbo64\bin\turbojpeg.dll`.
- **macOS**: `brew install jpeg-turbo`
- **Linux (Debian/Ubuntu)**: `sudo apt install libturbojpeg0`
- **Linux (Fedora/RHEL)**: `sudo dnf install libjpeg-turbo`

After installing, restart ComfyUI. PyTurboJPEG looks for the library via the system's standard shared-library search (and `LD_LIBRARY_PATH` on Linux), plus the default install paths above — installing to the default location is the most reliable option.

---

## License

MIT

## Author

**Pablo Apiolazza** — [APZmedia](https://github.com/APZmedia)

## ☕ Support

If this saved you time on a long batch run, consider buying me a coffee.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pabloapz)
