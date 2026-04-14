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
- **Parallel saving** — multi-threaded I/O for maximum throughput
- **Batch filename generation** — eliminates O(n²) collision checks
- **Optimized tensor operations** — minimal CPU-GPU transfer overhead
- **Compression control** — turn it off for maximum speed
- **Memory efficient** — no image duplication in output
- Suitable for high-volume batch and sequence output

---

## Performance Optimizations

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

---

## Installation

1. Clone this repo into your ComfyUI `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/APZmedia/APZmedia-comfyui-fast-image-save.git
   ```
2. Restart ComfyUI
3. Find the node under the **APZmedia Fast image save** category

---

## License

MIT

## Author

**Pablo Apiolazza** — [APZmedia](https://github.com/APZmedia)

## ☕ Support

If this saved you time on a long batch run, consider buying me a coffee.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pabloapz)
