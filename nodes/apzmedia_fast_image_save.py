import os
import cv2
import numpy as np
import folder_paths
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import torch

# Optional performance libraries - gracefully degrade if not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import turbojpeg
    try:
        # The PyTurboJPEG wheel only installs the Python wrapper; it still
        # needs the native libturbojpeg shared library on the system. When
        # that native library can't be located this raises (commonly a
        # RuntimeError/OSError, not an ImportError), so it must be caught
        # separately or it takes down the whole node import.
        _jpeg_encoder = turbojpeg.TurboJPEG()
        TURBOJPEG_AVAILABLE = True
    except Exception as e:
        print(f"[APZmedia Fast Image Save] PyTurboJPEG installed but the native "
              f"libturbojpeg library was not found ({e}). Falling back to OpenCV/PIL "
              f"for JPEG encoding. See README for how to install the native library.")
        TURBOJPEG_AVAILABLE = False
        _jpeg_encoder = None
except ImportError:
    TURBOJPEG_AVAILABLE = False
    _jpeg_encoder = None

try:
    import webp
    WEBP_AVAILABLE = True
except ImportError:
    WEBP_AVAILABLE = False

# Performance ranking per format (lower = faster)
BACKEND_RANKINGS = {
    'png': ['opencv', 'pil'],  # OpenCV faster for PNG
    'jpeg': ['turbojpeg', 'opencv', 'pil'],  # TurboJPEG fastest
    'webp': ['pil', 'webp', 'opencv'],  # PIL best WebP quality control
}


def get_fastest_backend(extension, preferred=None):
    """Return the fastest available backend for the given extension."""
    rankings = BACKEND_RANKINGS.get(extension, ['opencv'])

    if preferred and preferred in rankings:
        # Check if preferred is available
        if _is_backend_available(preferred):
            return preferred

    for backend in rankings:
        if _is_backend_available(backend):
            return backend

    return 'opencv'  # Always available fallback


def _is_backend_available(backend):
    """Check if a backend is available."""
    return {
        'opencv': True,  # Always available
        'pil': PIL_AVAILABLE,
        'turbojpeg': TURBOJPEG_AVAILABLE,
        'webp': WEBP_AVAILABLE,
    }.get(backend, False)


class FastImageSave:
    MAX_WORKERS = 4

    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
        backends = ['auto', 'opencv', 'pil']
        if TURBOJPEG_AVAILABLE:
            backends.append('turbojpeg')
        if WEBP_AVAILABLE:
            backends.append('webp-native')

        return {
            "required": {
                "images": ("IMAGE", ),
                "output_path": ("STRING", {"default": '[time(%Y-%m-%d)]', "multiline": False}),
                "filename_prefix": ("STRING", {"default": 'ComfyUI', "multiline": False}),
                "filename_delimiter": ("STRING", {"default": '_', "multiline": False}),
                "filename_number_padding": ("INT", {"default": 4, "min": 1, "max": 10}),
                "filename_number_start": (['false', 'true'], {"default": 'false'}),
                "extension": (['png', 'jpeg', 'webp'],),
                "dpi": ("INT", {"default": 300, "min": 1, "max": 600}),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100}),
                "optimize_image": (['false', 'true'], {"default": 'true'}),
                "lossless_webp": (['false', 'true'], {"default": 'false'}),
                "overwrite_mode": (['false', 'true'], {"default": 'false'}),
                "show_previews": (['false', 'true'], {"default": 'true'}),
            },
            # Kept optional (rather than required) so workflows and API prompts saved
            # before these inputs existed keep working without specifying them.
            "optional": {
                "parallel_save": (['false', 'true'], {"default": 'true'}),
                "max_workers": ("INT", {"default": 4, "min": 1, "max": 16}),
                "backend": (backends, {"default": 'auto', "tooltip":
                                       "auto = fastest available, opencv = always works, pil = best quality, "
                                       "turbojpeg = fastest JPEG (if installed), webp-native = WebP optimized (if installed)"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "save_files"
    OUTPUT_NODE = True
    CATEGORY = "APZmedia Fast image save"

    def save_files(self, images, output_path, filename_prefix, filename_delimiter, filename_number_padding,
                   filename_number_start, extension, dpi, quality, optimize_image, lossless_webp,
                   overwrite_mode, show_previews, parallel_save='true', max_workers=4, backend='auto'):
        output_path = self.get_output_path(output_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)

        # Determine actual backend
        if backend == 'auto':
            actual_backend = get_fastest_backend(extension)
        else:
            actual_backend = get_fastest_backend(extension, backend)

        start_num = 1 if filename_number_start == 'true' else 0
        optimize = optimize_image == 'true'
        lossless = lossless_webp == 'true'
        overwrite = overwrite_mode == 'true'
        parallel = parallel_save == 'true'

        filenames = self.save_images(images, output_path, filename_prefix, filename_delimiter,
                                     filename_number_padding, start_num, extension, dpi, quality,
                                     optimize, lossless, overwrite, parallel, max_workers, actual_backend)

        if show_previews == 'true':
            print(f"Images saved at: {output_path} (using {actual_backend})")

        if filenames:
            full_paths = [os.path.join(output_path, fname) for fname in filenames]
            return images, full_paths[-1]
        else:
            return images, "No images were saved."

    def get_output_path(self, output_path):
        return output_path.replace('[time(%Y-%m-%d)]', datetime.now().strftime('%Y-%m-%d'))

    def generate_filename_batch(self, output_path, filename_prefix, filename_delimiter,
                                start_count, extension, padding, count, overwrite_mode):
        """Generate unique filenames in batch to minimize disk I/O checks."""
        filenames = []
        existing_files = set()

        if not overwrite_mode:
            try:
                existing_files = {f.lower() for f in os.listdir(output_path)
                                  if f.lower().startswith(filename_prefix.lower())}
            except (OSError, IOError):
                pass

        for i in range(count):
            num = start_count + i
            filename = f"{filename_prefix}{filename_delimiter}{str(num).zfill(padding)}.{extension}"

            if not overwrite_mode and filename.lower() in existing_files:
                while True:
                    num += 1
                    filename = f"{filename_prefix}{filename_delimiter}{str(num).zfill(padding)}.{extension}"
                    if filename.lower() not in existing_files:
                        break

            filenames.append(filename)
            existing_files.add(filename.lower())

        return filenames

    def process_image_tensor(self, image):
        """Convert tensor to numpy array efficiently."""
        if isinstance(image, torch.Tensor):
            if image.device.type != 'cpu':
                image = image.cpu()
            img = (255.0 * image).numpy()
        else:
            img = 255.0 * image

        img = np.clip(img, 0, 255).astype(np.uint8)
        return img  # Return RGB for non-OpenCV backends

    def save_with_backend(self, file_path, img_rgb, extension, quality, optimize, lossless, backend, dpi):
        """Save image using specified backend."""
        if backend == 'opencv':
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            if extension == 'png':
                params = [cv2.IMWRITE_PNG_COMPRESSION, 9 if optimize else 1]
                cv2.imwrite(file_path, img_bgr, params)
            elif extension == 'jpeg':
                params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                cv2.imwrite(file_path, img_bgr, params)
            else:  # webp
                if lossless:
                    params = [int(cv2.IMWRITE_WEBP_QUALITY), 100]
                else:
                    params = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
                cv2.imwrite(file_path, img_bgr, params)

        elif backend == 'pil':
            pil_img = Image.fromarray(img_rgb)
            if extension == 'png':
                pil_img.save(file_path, 'PNG', optimize=optimize)
            elif extension == 'jpeg':
                pil_img.save(file_path, 'JPEG', quality=quality, optimize=optimize)
            else:  # webp
                method = 6 if optimize else 0  # 6 = slowest/best, 0 = fastest
                pil_img.save(file_path, 'WEBP', quality=quality, method=method,
                           lossless=lossless)

        elif backend == 'turbojpeg' and TURBOJPEG_AVAILABLE:
            # TurboJPEG is fastest for JPEG
            if extension == 'jpeg':
                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                with open(file_path, 'wb') as f:
                    f.write(_jpeg_encoder.encode(img_bgr, quality=quality))
            else:
                # Fallback to PIL for non-JPEG
                self.save_with_backend(file_path, img_rgb, extension, quality, optimize, lossless, 'pil', dpi)

        elif backend == 'webp-native' and WEBP_AVAILABLE:
            if extension == 'webp':
                # Use native WebP library for best WebP performance
                import io
                pil_img = Image.fromarray(img_rgb)
                buf = io.BytesIO()
                method = 6 if optimize else 0
                pil_img.save(buf, 'WEBP', quality=quality, method=method, lossless=lossless)
                with open(file_path, 'wb') as f:
                    f.write(buf.getvalue())
            else:
                self.save_with_backend(file_path, img_rgb, extension, quality, optimize, lossless, 'pil', dpi)

    def save_single_image(self, args):
        """Worker function for parallel saving."""
        file_path, img_rgb, extension, quality, optimize, lossless, backend, dpi = args

        try:
            self.save_with_backend(file_path, img_rgb, extension, quality, optimize, lossless, backend, dpi)
            return True
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
            return False

    def save_images(self, images, output_path, filename_prefix, filename_delimiter,
                    filename_number_padding, filename_number_start, extension, dpi, quality,
                    optimize_image, lossless_webp, overwrite_mode, parallel_save, max_workers, backend):

        if images is None or len(images) == 0:
            return []

        filenames = self.generate_filename_batch(
            output_path, filename_prefix, filename_delimiter,
            filename_number_start, extension, filename_number_padding,
            len(images), overwrite_mode
        )

        file_paths = [os.path.join(output_path, fname) for fname in filenames]

        if parallel_save and len(images) > 1:
            images_rgb = []
            for image in images:
                img_rgb = self.process_image_tensor(image)
                images_rgb.append(img_rgb)

            save_args = [
                (fp, img, extension, quality, optimize_image, lossless_webp, backend, dpi)
                for fp, img in zip(file_paths, images_rgb)
            ]

            workers = min(max_workers, len(images))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(self.save_single_image, save_args))

            return [fname for fname, success in zip(filenames, results) if success]

        else:
            for i, image in enumerate(images):
                img_rgb = self.process_image_tensor(image)
                file_path = file_paths[i]
                self.save_with_backend(file_path, img_rgb, extension, quality,
                                     optimize_image, lossless_webp, backend, dpi)

            return filenames


NODE_CLASS_MAPPINGS = {
    "APZmedia Fast image save": FastImageSave,
}
