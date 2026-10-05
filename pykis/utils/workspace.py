import os
import tempfile
from pathlib import Path


def get_workspace_path() -> Path:
    """Pykis의 기본 작업공간 폴더를 반환합니다."""
    return (Path.home() / ".pykis").resolve()


def get_cache_path() -> Path:
    """Pykis의 캐시 폴더를 반환합니다."""
    return (get_workspace_path() / "cache").resolve()


def write_private_text(path: "str | Path", text: str) -> None:
    """
    소유자만 읽고 쓸 수 있는 권한(0600)으로 텍스트 파일을 원자적으로 저장합니다.

    임시 파일에 먼저 쓴 뒤 교체하므로, 저장 도중 실패해도 기존 파일이 손상되지 않습니다.
    (Windows 등 POSIX 권한을 지원하지 않는 환경에서는 권한 설정이 무시될 수 있습니다.)
    """
    path = Path(path)
    # mkstemp는 0600 권한으로 파일을 생성합니다.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")

    try:
        # fdopen이 fd의 소유권을 가져가므로 이후에는 직접 close하지 않습니다.
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)

        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def ensure_private_dir(path: "str | Path") -> Path:
    """
    폴더를 생성합니다. 새로 만드는 폴더(상위 폴더 포함)만 소유자 전용(0700)으로 만들고,
    이미 있는 폴더의 권한은 변경하지 않습니다.
    """
    path = Path(path)
    missing = [p for p in (path, *path.parents) if not p.exists()]

    for directory in reversed(missing):
        try:
            directory.mkdir(mode=0o700, exist_ok=True)
        except FileNotFoundError:
            continue

    path.mkdir(parents=True, exist_ok=True)
    return path
