import os
import cv2
import numpy as np
import folder_paths
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import torch


class FastImageSave:
    MAX_WORKERS = 4  # Tunable based on disk I/O capacity

    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
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
                "parallel_save": (['false', 'true'], {"default": 'true'}),
                "max_workers": ("INT", {"default": 4, "min": 1, "max": 16}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "save_files"

    OUTPUT_NODE = True

    CATEGORY = "APZmedia Fast image save"

    def save_files(self, images, output_path, filename_prefix, filename_delimiter, filename_number_padding,
                   filename_number_start, extension, dpi, quality, optimize_image, lossless_webp,
                   overwrite_mode, show_previews, parallel_save, max_workers):
        output_path = self.get_output_path(output_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)

        start_num = 1 if filename_number_start == 'true' else 0
        optimize = optimize_image == 'true'
        lossless = lossless_webp == 'true'
        overwrite = overwrite_mode == 'true'
        parallel = parallel_save == 'true'

        filenames = self.save_images(images, output_path, filename_prefix, filename_delimiter,
                                     filename_number_padding, start_num, extension, dpi, quality,
                                     optimize, lossless, overwrite, parallel, max_workers)

        if show_previews == 'true':
            print(f"Images saved at: {output_path}")

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
            # Batch check: get all existing files with this prefix once
            try:
                existing_files = {f.lower() for f in os.listdir(output_path)
                                  if f.lower().startswith(filename_prefix.lower())}
            except (OSError, IOError):
                pass

        for i in range(count):
            num = start_count + i
            filename = f"{filename_prefix}{filename_delimiter}{str(num).zfill(padding)}.{extension}"

            if not overwrite_mode and filename.lower() in existing_files:
                # Find next available by incrementing
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
        # Ensure tensor is on CPU and contiguous for faster numpy conversion
        if isinstance(image, torch.Tensor):
            if image.device.type != 'cpu':
                image = image.cpu()
            img = (255.0 * image).numpy()
        else:
            img = 255.0 * image

        img = np.clip(img, 0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def save_single_image(self, args):
        """Worker function for parallel saving."""
        file_path, img_bgr, extension, quality, optimize, lossless = args

        try:
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
            return True
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
            return False

    def save_images(self, images, output_path, filename_prefix, filename_delimiter,
                    filename_number_padding, filename_number_start, extension, dpi, quality,
                    optimize_image, lossless_webp, overwrite_mode, parallel_save, max_workers):

        if images is None or len(images) == 0:
            return []

        # Pre-generate all filenames in batch
        filenames = self.generate_filename_batch(
            output_path, filename_prefix, filename_delimiter,
            filename_number_start, extension, filename_number_padding,
            len(images), overwrite_mode
        )

        # Pre-validate file paths
        file_paths = [os.path.join(output_path, fname) for fname in filenames]

        if parallel_save and len(images) > 1:
            # Parallel processing: convert tensors in main thread (GIL-sensitive),
            # save in worker threads (I/O-bound)

            # Batch convert all images first
            images_bgr = []
            for image in images:
                img_bgr = self.process_image_tensor(image)
                images_bgr.append(img_bgr)

            # Parallel save
            save_args = [
                (fp, img, extension, quality, optimize_image, lossless_webp)
                for fp, img in zip(file_paths, images_bgr)
            ]

            workers = min(max_workers, len(images))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(self.save_single_image, save_args))

            # Return only successfully saved filenames
            return [fname for fname, success in zip(filenames, results) if success]

        else:
            # Sequential processing
            for i, image in enumerate(images):
                img_bgr = self.process_image_tensor(image)
                file_path = file_paths[i]

                if extension == 'png':
                    params = [cv2.IMWRITE_PNG_COMPRESSION, 9 if optimize_image else 1]
                    cv2.imwrite(file_path, img_bgr, params)
                elif extension == 'jpeg':
                    params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                    cv2.imwrite(file_path, img_bgr, params)
                else:  # webp
                    if lossless_webp:
                        params = [int(cv2.IMWRITE_WEBP_QUALITY), 100]
                    else:
                        params = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
                    cv2.imwrite(file_path, img_bgr, params)

            return filenames


NODE_CLASS_MAPPINGS = {
    "APZmedia Fast image save": FastImageSave,
}
