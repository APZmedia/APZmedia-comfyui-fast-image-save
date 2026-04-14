import subprocess
import sys
import os


def _install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _check_and_install_optional_deps():
    """Check and install optional performance libraries on first load."""
    # Flag file to track if we've attempted install
    flag_file = os.path.join(os.path.dirname(__file__), ".optional_deps_checked")

    if os.path.exists(flag_file):
        return

    # Create flag immediately to prevent re-runs
    try:
        with open(flag_file, 'w') as f:
            f.write('checked')
    except Exception:
        pass

    # Check what's missing and try to install
    missing = []

    try:
        import turbojpeg
    except ImportError:
        missing.append("PyTurboJPEG")

    try:
        import webp
    except ImportError:
        missing.append("webp")

    if missing:
        print(f"[APZmedia Fast Image Save] Installing optional performance libraries: {', '.join(missing)}...")
        for pkg in missing:
            if _install_package(pkg):
                print(f"[APZmedia Fast Image Save] Installed {pkg}")
            else:
                print(f"[APZmedia Fast Image Save] Failed to install {pkg} (install manually with: pip install {pkg})")

        print("[APZmedia Fast Image Save] Restart ComfyUI to use newly installed libraries")


# Run on module load
_check_and_install_optional_deps()

# Import and export the node
from .nodes.apzmedia_fast_image_save import FastImageSave

NODE_CLASS_MAPPINGS = {
    "APZmedia Fast image save": FastImageSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "APZmedia Fast image save": "APZmedia Fast Image Save Node",
}
