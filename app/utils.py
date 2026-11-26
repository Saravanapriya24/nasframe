import os
import re
import uuid
from flask import current_app
from PIL import Image, ImageOps
from app.models import Product, Category, SiteSettings

FORMAT_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_SIDE = 1600


class UploadError(Exception):
    pass


def save_image(file_storage):
    """Validate and save an uploaded image. Returns the new safe filename."""
    if not file_storage or not file_storage.filename:
        raise UploadError("Please choose an image file.")
    name = file_storage.filename.lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise UploadError("Only JPG, JPEG, PNG and WebP images are allowed.")
    if file_storage.mimetype not in ALLOWED_MIME:
        raise UploadError("This file type is not allowed.")
    try:
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        fmt = img.format
        if fmt not in FORMAT_EXT:
            raise UploadError("Only JPG, PNG and WebP images are allowed.")
        img = ImageOps.exif_transpose(img)
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        if fmt == "JPEG" and img.mode != "RGB":
            img = img.convert("RGB")
        filename = f"{uuid.uuid4().hex}.{FORMAT_EXT[fmt]}"
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        img.save(path, fmt, quality=85, optimize=True)
        return filename
    except UploadError:
        raise
    except Exception:
        raise UploadError("This file is not a valid image.")


def image_in_use(filename):
    if Product.query.filter_by(image_filename=filename).first():
        return True
    if Category.query.filter_by(image_filename=filename).first():
        return True
    s = SiteSettings.query.filter(
        (SiteSettings.logo_filename == filename) |
        (SiteSettings.banner_filename == filename)).first()
    return s is not None


def delete_image_if_unused(filename):
    """Delete the file only if no record still references it."""
    if not filename or image_in_use(filename):
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if os.path.isfile(path):
        os.remove(path)


def normalize_size(raw):
    """'12x8', '12*8', '12 X 8' -> '12 × 8'. Returns None if invalid."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*", raw or "")
    return f"{m.group(1)} × {m.group(2)}" if m else None