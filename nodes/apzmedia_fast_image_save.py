import os
import cv2
import numpy as np
import folder_paths
from datetime import datetime


class FastImageSave:
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
            },
            "optional": {},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "save_files"

    OUTPUT_NODE = True

    CATEGORY = "APZmedia Fast image save"

    def save_files(self, images, output_path, filename_prefix, filename_delimiter, filename_number_padding,
                   filename_number_start, extension, dpi, quality, optimize_image, lossless_webp,
                   overwrite_mode, show_previews):
        print("Entered save_files method")
        print("Images:", images)
        print("Output path:", output_path)
        
        output_path = self.get_output_path(output_path)
        print("Processed output path:", output_path)
        
        if not os.path.exists(output_path):
            print(f'The path `{output_path}` does not exist! Creating directory.')
            os.makedirs(output_path, exist_ok=True)

        filenames, saved_images = self.save_images(images, output_path, filename_prefix, filename_delimiter, filename_number_padding,
                                     filename_number_start == 'true', extension, dpi, quality, optimize_image == 'true', 
                                     lossless_webp == 'true', overwrite_mode == 'true')

        print("Filenames generated:", filenames)

        if show_previews == 'true':
            print(f"Images saved at: {output_path}")
        
        if filenames is None:
            filenames = []

        # Output both the saved images and their filenames
        if filenames:
            full_paths = [os.path.join(output_path, fname) for fname in filenames]
            return saved_images, f"{full_paths[-1]}"
        else:
            print("No images were saved.")
            return images, "No images were saved."

    def get_output_path(self, output_path):
        print(f"Original output path: {output_path}")
        processed_output_path = output_path.replace('[time(%Y-%m-%d)]', datetime.now().strftime('%Y-%m-%d'))
        print(f"Processed output path: {processed_output_path}")
        return processed_output_path

    def generate_unique_filename(self, output_path, filename_prefix, filename_delimiter, img_count, extension, filename_number_padding, overwrite_mode):
        while True:
            filename = f"{filename_prefix}{filename_delimiter}{str(img_count).zfill(filename_number_padding)}.{extension}"
            file_path = os.path.join(output_path, filename)

            if not overwrite_mode and os.path.exists(file_path):
                print(f"File {file_path} already exists, trying next filename.")
                img_count += 1
            else:
                return filename, file_path

    def save_images(self, images, output_path, filename_prefix, filename_delimiter, filename_number_padding,
                    filename_number_start, extension, dpi, quality, optimize_image, lossless_webp,
                    overwrite_mode):
        img_count = 1 if filename_number_start else 0
        filenames = []
        saved_images = []

        if images is None or images.numel() == 0:
            print("No images found.")
            return filenames, saved_images

        for idx, image in enumerate(images):
            print(f"Processing image {idx + 1}/{len(images)}")
            print(f"Current image tensor: {image}")
            
            i = 255. * image.cpu().numpy()
            img = np.clip(i, 0, 255).astype(np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            filename, file_path = self.generate_unique_filename(output_path, filename_prefix, filename_delimiter, img_count, extension, filename_number_padding, overwrite_mode)

            print(f"Generated filename: {filename}")
            print(f"Full file path: {file_path}")

            if extension == 'png':
                self.save_png(file_path, img, dpi, optimize_image)
            else:
                self.save_jpeg_or_webp(file_path, img, extension, quality, lossless_webp)

            filenames.append(filename)
            saved_images.append(image)
            img_count += 1

        return filenames, saved_images

    def save_png(self, file_path, img, dpi, optimize_image):
        print(f"Saving PNG to {file_path}")
        print(f"PNG optimization: {optimize_image}")
        
        params = [cv2.IMWRITE_PNG_COMPRESSION, 9 if optimize_image else 0]
        cv2.imwrite(file_path, img, params)

    def save_jpeg_or_webp(self, file_path, img, extension, quality, lossless_webp):
        print(f"Saving {extension.upper()} to {file_path}")
        print(f"Quality: {quality}")
        print(f"Lossless WebP: {lossless_webp}")

        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality] if extension == 'jpeg' else [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        cv2.imwrite(file_path, img, params)


NODE_CLASS_MAPPINGS = {
    "APZmedia Fast image save": FastImageSave,
}
