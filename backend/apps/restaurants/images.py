"""Bounded raster decoding and re-encoding; never serve original uploads."""

import warnings
from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers


class LogoSerializer(serializers.Serializer):
    logo = serializers.FileField()

    def to_internal_value(self, data):
        if set(data.keys()) != {"logo"}:
            raise serializers.ValidationError({"logo": "Send only the logo file."})
        return super().to_internal_value(data)

    def validate_logo(self, upload):
        if upload.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Choose an image of 2 MB or less.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(upload)
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise serializers.ValidationError("Use a PNG, JPEG or WebP image.")
                if image.width > 2048 or image.height > 2048:
                    raise serializers.ValidationError(
                        "Logo dimensions must not exceed 2048 × 2048 pixels."
                    )
                image.verify()
                upload.seek(0)
                with Image.open(upload) as source:
                    normalized = ImageOps.exif_transpose(source).convert("RGBA")
                    normalized.info.clear()
                    output = BytesIO()
                    normalized.save(output, format="PNG")
            return ContentFile(output.getvalue(), name=f"{uuid4().hex}.png")
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ) as error:
            raise serializers.ValidationError(
                "This file is not a supported, valid image."
            ) from error
