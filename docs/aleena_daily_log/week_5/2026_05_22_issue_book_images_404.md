# Daily Log: Book Image Loading Issue (404 Not Found)
**Date:** May 22, 2026

## Summary of the Issue
When viewing the Climate Academy Student Book via the browser client, all images inside the book iframe failed to load. The browser console showed HTTP `404 Not Found` errors for image endpoints like `/input/media/image1.png`.

## Detailed Root Cause Analysis
1. **Annotated HTML File Preference**:
   The FastAPI server endpoints load the book HTML by calling `resolve_book_html_path()`. This checks if an annotated version of the student book exists (`encyclopedia/output/full_student_book_annotated.html`) and prefers it over the raw un-annotated book.
2. **Re-written Relative Paths**:
   Inside the annotated HTML, the annotation pipeline correctly rewrote the image source attributes relative to its location under `encyclopedia/output/`. Thus, the source paths were formatted as relative paths going up two levels: `../../input/media/image1.png`.
3. **Inlining Logic in `inline_local_images()`**:
   To make local images display inside the component iframe, the `inline_local_images` function attempts to base64-inline all `<img src="...">` elements:
   ```python
   image_path = (base_dir / clean_src).resolve()
   try:
       image_path.relative_to(base_dir)
   except ValueError:
       continue
   ```
4. **Validation Failure**:
   * `base_dir` resolves to `c:\...\chatbot\encyclopedia\output`.
   * `image_path` resolves to the correct location on disk at `c:\...\chatbot\input\media\image1.png`.
   * However, `image_path.relative_to(base_dir)` raises a `ValueError` because the `input/media` directory is located outside (and is not a child of) `encyclopedia/output/`.
   * This exception causes the code to trigger the `continue` statement, completely skipping the base64-inlining step.
5. **Browser Resolution and 404**:
   Since the inlining was skipped, the raw HTML with `src="../../input/media/image1.png"` was served to the client browser relative to the `/book/document` endpoint. The browser resolved this to `/input/media/image1.png` on the host, causing Uvicorn to respond with a 404 because the endpoint does not exist.
