import os
import json
import sys
from pathlib import Path

def generate_pdf_metadata(folder_path):
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"The provided path '{folder_path}' is not a valid directory.")

    result = []

    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() == ".pdf":
            full_path = str(file.resolve())
            name = file.stem
            metadata = {
                "Location": full_path,
                "Name": name,
                "Description": name
            }
            result.append(metadata)

    return result

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    try:
        metadata_list = generate_pdf_metadata(folder_path)
        print(json.dumps(metadata_list, indent=4))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()