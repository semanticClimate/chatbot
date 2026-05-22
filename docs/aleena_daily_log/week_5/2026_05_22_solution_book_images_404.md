# Daily Log: Solution for Book Image Loading Issue (404 Not Found)
**Date:** May 22, 2026

## Proposed Solution
To fix the image loading issue while preserving the path-traversal/security validation in the codebase, the scope of the path validation was expanded from the parent directory of the book HTML (`base_dir`) to the **project root directory** (`project_root`). 

Since `input/media` resides inside the project root, the validation passes for all internal book images, but still rejects any files located outside the project directory.

## Implementation Details

We modified `inline_local_images()` in both `climate_streamlit/rag/book_document.py` and `climate_streamlit/app.py`:

### 1. Changes in `climate_streamlit/rag/book_document.py`
We used the existing `_PKG_DIR` module-level variable (`Path(__file__).resolve().parent.parent`) to find the project root:
```python
def inline_local_images(html: str, base_dir: Path) -> str:
    soup = BeautifulSoup(html, "html.parser")
    base_dir = base_dir.resolve()
    project_root = _PKG_DIR.parent.resolve()

    for img in soup.find_all("img"):
        # ...
        clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0])
        image_path = (base_dir / clean_src).resolve()
        try:
            image_path.relative_to(project_root)
        except ValueError:
            continue
```

### 2. Changes in `climate_streamlit/app.py`
We used the existing `ROOT_DIR` global variable (`Path(__file__).resolve().parent.parent`) to find the project root:
```python
def inline_local_images(html: str, base_dir: Path) -> str:
    soup = BeautifulSoup(html, "html.parser")
    base_dir = base_dir.resolve()
    project_root = ROOT_DIR.resolve()

    for img in soup.find_all("img"):
        # ...
        clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0])
        image_path = (base_dir / clean_src).resolve()
        try:
            image_path.relative_to(project_root)
        except ValueError:
            continue
```

## Outcome and Verification
1. Both the Streamlit interface and the FastAPI sidecar server now successfully base64-inline the book images during HTML rendering.
2. The browser successfully displays the book diagrams and images without raising any `404 Not Found` requests.
3. Secure path-traversal limits are maintained by ensuring that no file outside of the project root directory is loaded or inlined.
