from pathlib import Path
from PIL import Image

# Get project root (parent of scripts folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Correct media folder path
MEDIA_FOLDER = BASE_DIR / "input" / "media"

print(f"\nSearching inside: {MEDIA_FOLDER}\n")

# Find all EMF files
emf_files = MEDIA_FOLDER.glob("*.emf")

for emf_file in emf_files:
    try:
        print(f"INPUT FILE : {emf_file}")

        # Open EMF image
        img = Image.open(emf_file)

        # Output PNG path
        output_file = emf_file.with_suffix(".png")

        # Save PNG
        img.save(output_file, "PNG")

        print(f"OUTPUT FILE: {output_file}")
        print(f"Converted: {emf_file.name} -> {output_file.name}\n")

    except Exception as e:
        print(f"Failed to convert {emf_file.name}")
        print(f"Error: {e}\n")

print("Done!")