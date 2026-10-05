import os
from os import PathLike

__all__ = [
    "write_private_text",
]


def write_private_text(path: str | PathLike[str], text: str) -> None:
    """소유자만 읽고 쓸 수 있는 권한(0600)으로 텍스트 파일을 저장합니다."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)

    # 이미 존재하던 파일의 권한도 제한합니다. (Windows에서는 무시될 수 있습니다.)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
