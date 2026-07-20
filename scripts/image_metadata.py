#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small standard-library image metadata reader used by pipeline validators.

Supported formats:
- PNG: dimensions and alpha capability, including tRNS transparency
- JPEG: dimensions
- WebP: VP8X, VP8L, and VP8 dimensions

The production pipeline normally emits PNG assets, while reference images may
be PNG, JPEG, or WebP. Unsupported formats are reported explicitly instead of
guessed.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}


class ImageMetadataError(ValueError):
    pass


def read_image_metadata(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        header = handle.read(32)
        if header.startswith(PNG_SIGNATURE):
            return _read_png(path, header)
        if header.startswith(b"\xff\xd8"):
            handle.seek(0)
            return _read_jpeg(path, handle)
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return _read_webp(path, header)
    raise ImageMetadataError(f"unsupported image format: {path.suffix or 'unknown'}")


def _read_png(path: Path, header: bytes) -> dict[str, Any]:
    if len(header) < 26 or header[12:16] != b"IHDR":
        raise ImageMetadataError("invalid PNG: missing IHDR")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise ImageMetadataError("invalid PNG dimensions")
    color_type = header[25]
    has_trns = False
    with path.open("rb") as handle:
        handle.seek(8)
        while True:
            length_bytes = handle.read(4)
            chunk_type = handle.read(4)
            if len(length_bytes) != 4 or len(chunk_type) != 4:
                break
            chunk_length = struct.unpack(">I", length_bytes)[0]
            if chunk_type == b"tRNS":
                has_trns = True
            handle.seek(chunk_length + 4, 1)
            if chunk_type in {b"IDAT", b"IEND"}:
                break
    return {
        "format": "png",
        "width": width,
        "height": height,
        "hasAlphaCapability": color_type in {4, 6} or has_trns,
        "colorType": color_type,
        "path": str(path),
    }


def _read_jpeg(path: Path, handle: Any) -> dict[str, Any]:
    if handle.read(2) != b"\xff\xd8":
        raise ImageMetadataError("invalid JPEG signature")

    while True:
        byte = handle.read(1)
        if not byte:
            break
        if byte != b"\xff":
            continue
        while byte == b"\xff":
            byte = handle.read(1)
        if not byte:
            break
        marker = byte[0]
        if marker in {0xD8, 0xD9}:
            continue
        length_bytes = handle.read(2)
        if len(length_bytes) != 2:
            break
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            raise ImageMetadataError("invalid JPEG segment length")
        if marker in JPEG_SOF_MARKERS:
            payload = handle.read(segment_length - 2)
            if len(payload) < 5:
                raise ImageMetadataError("invalid JPEG SOF segment")
            height, width = struct.unpack(">HH", payload[1:5])
            if width <= 0 or height <= 0:
                raise ImageMetadataError("invalid JPEG dimensions")
            return {
                "format": "jpeg",
                "width": width,
                "height": height,
                "hasAlphaCapability": False,
                "path": str(path),
            }
        handle.seek(segment_length - 2, 1)

    raise ImageMetadataError("JPEG dimensions not found")


def _read_webp(path: Path, header: bytes) -> dict[str, Any]:
    if len(header) < 30:
        raise ImageMetadataError("invalid WebP header")
    chunk_type = header[12:16]
    data = header[20:]

    if chunk_type == b"VP8X":
        if len(data) < 10:
            raise ImageMetadataError("invalid VP8X header")
        flags = data[0]
        width = 1 + int.from_bytes(data[4:7], "little")
        height = 1 + int.from_bytes(data[7:10], "little")
        has_alpha = bool(flags & 0x10)
    elif chunk_type == b"VP8L":
        if len(data) < 5 or data[0] != 0x2F:
            raise ImageMetadataError("invalid VP8L header")
        b1, b2, b3, b4 = data[1:5]
        width = 1 + (b1 | ((b2 & 0x3F) << 8))
        height = 1 + ((b2 >> 6) | (b3 << 2) | ((b4 & 0x0F) << 10))
        has_alpha = True
    elif chunk_type == b"VP8 ":
        if len(data) < 10 or data[3:6] != b"\x9d\x01\x2a":
            raise ImageMetadataError("invalid VP8 frame header")
        width = int.from_bytes(data[6:8], "little") & 0x3FFF
        height = int.from_bytes(data[8:10], "little") & 0x3FFF
        has_alpha = False
    else:
        raise ImageMetadataError(f"unsupported WebP chunk: {chunk_type!r}")

    if width <= 0 or height <= 0:
        raise ImageMetadataError("invalid WebP dimensions")
    return {
        "format": "webp",
        "width": width,
        "height": height,
        "hasAlphaCapability": has_alpha,
        "path": str(path),
    }
