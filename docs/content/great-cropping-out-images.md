# Content note: “The Great Cropping Out” images (#20)

In `input/full_student_book.html`, **Picture A** (figure) and **Picture B** both reference `media/image46.jpeg`. The narrative is that Picture B is the cropped wire photo (Vanessa Nakate removed). Picture B should use a **distinct asset** (cropped variant), not the same file as Picture A.

## Fix when asset is available

1. Add the cropped image to `input/media/` (e.g. `image46b.jpeg` or restore from AP crop).
2. Update Picture B `<img src="...">` (~line 3691) to point at that file.
3. Re-run encyclopedia annotation if the book HTML is regenerated.

Until then, the viewer will show the same image twice — a **content** gap, not a viewer bug.
