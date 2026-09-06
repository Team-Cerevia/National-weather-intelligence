"""Perceptual Image Hashing (pHash) and EXIF Metadata Extraction."""

import hashlib
from typing import Any

try:
    from PIL import ExifTags, Image

    HAS_PIL = True
except ImportError:
    Image = None
    ExifTags = None
    HAS_PIL = False


class ImageDeduplicator:
    """Provides perceptual image hashing (pHash/dHash) for duplicate image detection and EXIF metadata extraction."""

    @staticmethod
    def compute_phash(image_path_or_file: Any) -> str:
        """Computes a perceptual hash (dHash) for image duplicate detection across social media posts."""
        try:
            with Image.open(image_path_or_file) as img:
                # Convert to grayscale and resize to 9x8 for difference hash
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())

                # Compute difference between adjacent pixels
                diff = []
                for row in range(8):
                    for col in range(8):
                        left = pixels[row * 9 + col]
                        right = pixels[row * 9 + col + 1]
                        diff.append(left > right)

                # Convert boolean array to hex hash
                decimal_val = 0
                for bit in diff:
                    decimal_val = (decimal_val << 1) | int(bit)
                return f"{decimal_val:016x}"
        except Exception:
            # Fallback to MD5 hex string if image decoding fails
            if isinstance(image_path_or_file, (str, bytes)):
                content = (
                    str(image_path_or_file).encode("utf-8")
                    if isinstance(image_path_or_file, str)
                    else image_path_or_file
                )
                return hashlib.md5(content).hexdigest()[:16]
            return "0000000000000000"

    @staticmethod
    def is_duplicate(hash1: str, hash2: str, max_hamming_distance: int = 5) -> bool:
        """Checks if two images are duplicates by calculating Hamming distance between their perceptual hashes."""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return False
        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            # XOR to find differing bits
            xor_val = val1 ^ val2
            # Count set bits (Hamming distance)
            distance = bin(xor_val).count("1")
            return distance <= max_hamming_distance
        except ValueError:
            return hash1 == hash2

    @staticmethod
    def extract_exif_metadata(image_path_or_file: Any) -> dict[str, Any]:
        """Extracts camera EXIF metadata including GPS coordinates and exact capture timestamp."""
        metadata: dict[str, Any] = {}
        try:
            with Image.open(image_path_or_file) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return metadata

                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items() if k in ExifTags.TAGS}

                # Capture Timestamp
                if "DateTimeOriginal" in exif:
                    metadata["captured_at"] = str(exif["DateTimeOriginal"])
                elif "DateTime" in exif:
                    metadata["captured_at"] = str(exif["DateTime"])

                # Camera Details
                if "Make" in exif:
                    metadata["camera_make"] = str(exif["Make"])
                if "Model" in exif:
                    metadata["camera_model"] = str(exif["Model"])

                # GPS Coordinates
                if "GPSInfo" in exif:
                    gps_info = exif["GPSInfo"]
                    # Extract latitude & longitude if present
                    if 2 in gps_info and 4 in gps_info:  # 2: Lat, 4: Lon
                        lat_tuple = gps_info[2]
                        lon_tuple = gps_info[4]
                        lat_ref = gps_info.get(1, "N")
                        lon_ref = gps_info.get(3, "E")

                        lat = lat_tuple[0] + lat_tuple[1] / 60.0 + lat_tuple[2] / 3600.0
                        lon = lon_tuple[0] + lon_tuple[1] / 60.0 + lon_tuple[2] / 3600.0

                        if lat_ref == "S":
                            lat = -lat
                        if lon_ref == "W":
                            lon = -lon

                        metadata["latitude"] = round(float(lat), 6)
                        metadata["longitude"] = round(float(lon), 6)
        except Exception:
            pass

        return metadata
