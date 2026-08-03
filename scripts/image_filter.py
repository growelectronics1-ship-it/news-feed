python
#!/usr/bin/env python3
"""
image_filter.py

Decides whether a candidate article image is allowed to appear on the site.

HOW IT WORKS
------------
Each image is downloaded and run through DeepFace's face detector +
gender classifier (https://github.com/serengil/deepface). If ANY detected
face is classified as female, the image is rejected. If no face is detected,
or DeepFace errors out, the image is treated as "unknown" and handled
according to ON_UNCERTAIN below.

IMPORTANT LIMITATIONS (please read)
------------------------------------
Automatic gender classification from a photo is NOT reliable:
  - It will miss some photos of women (false negatives) - profile shots,
    partial faces, low resolution, unusual angles, sunglasses/hats, etc.
  - It will sometimes flag photos of men or of no one at all (false
    positives), especially on illustrations, graphics, or low-quality crops.
  - Gender classifiers are trained on limited data and are known to be
    less accurate for some ethnicities, ages, and gender-nonconforming
    presentations.
There is no way to make this 100% accurate. If you need a *guaranteed*
zero-images-of-women result, the only fully reliable option is to not show
photos at all (set ALLOW_ANY_IMAGES = False below to disable images site-wide).

ON_UNCERTAIN controls what happens when the model can't make a confident
call (no face found, or an error occurred):
  "keep"  - show the image anyway (default; maximizes how many articles get
            a picture, at the cost of occasionally letting an unclear photo
            of a woman through if the face wasn't detected).
  "drop"  - hide the image (stricter; you'll get more text-only cards, but
            fewer chances of the filter being fooled).
"""
import io
import os

import requests

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # don't bother downloading huge images
REQUEST_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (compatible; SimpleNewsBot/1.0; +https://example.com)"

# Set to False to disable ALL images on the site (the only 100%-guaranteed option).
ALLOW_ANY_IMAGES = True

# "keep" or "drop" - see docstring above.
ON_UNCERTAIN = os.environ.get("ON_UNCERTAIN_IMAGE", "keep")

_deepface_analyze = None  # lazy-loaded, see _get_deepface()


def _get_deepface():
    """Import DeepFace lazily so the script doesn't pay the (large) import
    cost when there are no images to check, and so a missing/broken
    DeepFace install doesn't crash the whole news fetch."""
    global _deepface_analyze
    if _deepface_analyze is None:
        from deepface import DeepFace
        _deepface_analyze = DeepFace.analyze
    return _deepface_analyze


def _download_image(url):
    resp = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        stream=True,
    )
    resp.raise_for_status()
    content = resp.raw.read(MAX_IMAGE_BYTES + 1, decode_content=True)
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("image too large")
    return content


def should_keep_image(image_url):
    """Return True if the image is safe to display, False if it should be
    dropped (article will just show without a picture)."""
    if not ALLOW_ANY_IMAGES:
        return False
    if not image_url:
        return False

    try:
        raw = _download_image(image_url)
    except Exception as exc:
        print(f"  [image_filter] could not download {image_url}: {exc}")
        return ON_UNCERTAIN == "keep"

    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img_array = np.array(img)

        analyze = _get_deepface()
        results = analyze(
            img_path=img_array,
            actions=["gender"],
            enforce_detection=False,  # don't throw when no face is found
            silent=True,
        )
        if isinstance(results, dict):
            results = [results]

        faces_found = [r for r in results if r.get("region", {}).get("w", 0) > 0]

        if not faces_found:
            return ON_UNCERTAIN == "keep"

        for face in faces_found:
            if face.get("dominant_gender") == "Woman":
                return False

        return True

    except Exception as exc:
        print(f"  [image_filter] classification failed for {image_url}: {exc}")
        return ON_UNCERTAIN == "keep"
