# PDF Metadata Extractor

This Python script (`app.py`) scans a folder for PDF files and generates a single JSON array containing metadata for each PDF. The metadata includes:

- **Location**: Full path to the PDF file.
- **Name**: File name without the `.pdf` extension.
- **Description**: Same as the file name.

## Usage

### Requirements
- Python 3.6 or later

### Running the Script

```bash
python app.py <folder_path>
```

Replace `<folder_path>` with the absolute or relative path to the directory containing the PDF files.

### Example
```bash
python app.py ./documents
```

This will output a JSON array to the console like the following:

```json
[
    {
        "Location": "/absolute/path/to/file1.pdf",
        "Name": "file1",
        "Description": "file1"
    },
    {
        "Location": "/absolute/path/to/file2.pdf",
        "Name": "file2",
        "Description": "file2"
    }
]
```

## Notes
- Only files with the `.pdf` extension are processed.
- Output is printed to standard output.
- Ensure that the folder path provided exists and contains PDF files.

