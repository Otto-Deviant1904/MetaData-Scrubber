from pathlib import Path
import tempfile
import shutil
import os
import errno
from enum import Enum
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError



class ResultType(Enum):
    SUCCESS = "success"
    ERROR = "error"


class ErrorCategory(Enum):
    INPUT_ERROR = "input_error"
    PERMISSION_ERROR = "permission_error"
    OUTPUT_ERROR = "output_error"
    PROCESSING_ERROR = "processing_error"


@dataclass
class ScrubResult:
    result_type: ResultType
    input_path: Path
    output_path: Path | None = None
    error: str | None = None
    error_category: ErrorCategory | None = None
    fix_hint: str | None = None
    metadata_removed: str | None = None

    def is_error(self) -> bool:
        return self.result_type == ResultType.ERROR


class ImageScrubber:
    """Scrubs metadata from image files."""

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        return path.suffix.lower() in cls.SUPPORTED_FORMATS

    @classmethod
    def scrub(cls, input_path: Path, output_path: Path) -> ScrubResult:
        # ---- input validation ----
        if not input_path.exists():
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error="File not found",
                error_category=ErrorCategory.INPUT_ERROR,
                fix_hint="Verify the input file path"
            )

        if not cls.can_handle(input_path):
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error="Unsupported image format",
                error_category=ErrorCategory.INPUT_ERROR,
                fix_hint=f"Supported formats: {', '.join(cls.SUPPORTED_FORMATS)}"
            )

        if not os.access(input_path, os.R_OK):
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error="Cannot read input file",
                error_category=ErrorCategory.PERMISSION_ERROR,
                fix_hint="Check file permissions"
            )

        # Output Directory
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if not os.access(output_path.parent, os.W_OK):
                raise PermissionError
        except PermissionError:
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error="Cannot write to output directory",
                error_category=ErrorCategory.PERMISSION_ERROR,
                fix_hint="Choose a writable output location"
            )

        tmp_path = None

        try:
            # temp file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=output_path.suffix,
                dir=output_path.parent
            ) as tmp:
                tmp_path = Path(tmp.name)

            # image processing
            with Image.open(input_path) as img:
                if not img.format:
                    raise ValueError("Unknown image format")

                # pixel-only copy -> drops all metadata
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(list(img.getdata()))

                fmt = img.format.upper()

                if fmt == "JPEG":
                    clean_img.save(tmp_path, "JPEG", quality=95, optimize=True)
                elif fmt == "PNG":
                    clean_img.save(tmp_path, "PNG", optimize=True)
                elif fmt == "WEBP":
                    clean_img.save(tmp_path, "WEBP", quality=95)
                else:
                    clean_img.save(tmp_path, fmt)

            shutil.move(str(tmp_path), str(output_path))
            tmp_path = None

            return ScrubResult(
                result_type=ResultType.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                metadata_removed="EXIF / IPTC / XMP metadata"
            )

        except UnidentifiedImageError:
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error="Invalid or corrupted image file",
                error_category=ErrorCategory.INPUT_ERROR,
                fix_hint="Upload a valid JPG, PNG, or WebP image"
            )

        except OSError as e:
            if e.errno == errno.ENOSPC:
                msg = "No space left on device"
                hint = "Free disk space"
            elif e.errno == errno.EROFS:
                msg = "Filesystem is read-only"
                hint = "Choose a writable output directory"
            else:
                msg = f"I/O error: {e}"
                hint = "Check disk health and permissions"

            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error=msg,
                error_category=ErrorCategory.OUTPUT_ERROR,
                fix_hint=hint
            )

        except Exception as e:
            return ScrubResult(
                result_type=ResultType.ERROR,
                input_path=input_path,
                error=f"Processing failed: {type(e).__name__}: {e}",
                error_category=ErrorCategory.PROCESSING_ERROR,
                fix_hint="Image may be corrupted or malformed"
            )

        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
