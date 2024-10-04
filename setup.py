from setuptools import setup, find_packages

setup(
    name="apzmedia_fast_image_save",
    version="0.1",  # Initial version, feel free to update as needed
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'some_dependency',  # Replace this with any real dependencies your project requires
    ],
    entry_points={
        'comfyui.nodes': [
            'fast_image_save_node = nodes.apzmedia_fast_image_save:FastImageSave',  
        ],
    },
    author="Pablo Apiolazza",  # Assuming based on the previous example
    author_email="info@apzmedia.com",  # Update if necessary
    description="A ComfyUI node to quickly save images with fast processing.",
    url="https://github.com/apzmedia/ComfyUI-APZmedia-fast-image-save",  # Update with your project's URL
    python_requires='>=3.6',
)
