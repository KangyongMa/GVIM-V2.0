r"""Windows filesystem path helpers.

DeerFlow's per-user, per-thread runtime layout can exceed the legacy Windows
MAX_PATH limit when users upload documents with long names. Python surfaces
that as FileNotFoundError unless the path is passed to Win32 with the extended
length prefix.
"""

import os


def extended_path(path: str | os.PathLike[str]) -> str:
    r"""Return *path* with a Windows extended-length prefix when needed.

    Non-Windows platforms receive the original filesystem path string. On
    Windows, absolute drive paths become ``\\?\C:\...`` and UNC paths become
    ``\\?\UNC\server\share\...``. Relative paths are made absolute first so
    the prefix is valid.
    """
    raw = os.fspath(path)
    if os.name != "nt":
        return raw

    if raw.startswith("\\\\?\\"):
        return raw

    absolute = os.path.abspath(raw)
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute


def open_long_path(path: str | os.PathLike[str], *args, **kwargs):
    """Open a path while bypassing Windows MAX_PATH limitations."""
    return open(extended_path(path), *args, **kwargs)


def read_bytes_long_path(path: str | os.PathLike[str]) -> bytes:
    """Read bytes while bypassing Windows MAX_PATH limitations."""
    with open_long_path(path, "rb") as f:
        return f.read()


def read_text_long_path(path: str | os.PathLike[str], *, encoding: str = "utf-8") -> str:
    """Read text while bypassing Windows MAX_PATH limitations."""
    with open_long_path(path, encoding=encoding) as f:
        return f.read()


def unlink_long_path(path: str | os.PathLike[str], *, missing_ok: bool = False) -> None:
    """Unlink a path while bypassing Windows MAX_PATH limitations."""
    try:
        os.unlink(extended_path(path))
    except FileNotFoundError:
        if not missing_ok:
            raise


def is_file_long_path(path: str | os.PathLike[str]) -> bool:
    """Return whether a path is a file while bypassing Windows MAX_PATH limits."""
    return os.path.isfile(extended_path(path))


def exists_long_path(path: str | os.PathLike[str]) -> bool:
    """Return whether a path exists while bypassing Windows MAX_PATH limits."""
    return os.path.exists(extended_path(path))


def requires_extended_path(path: str | os.PathLike[str]) -> bool:
    """Return whether Windows needs the extended-length prefix for this path."""
    return os.name == "nt" and len(os.path.abspath(os.fspath(path))) >= 260
