from pathlib import Path


def get_workspace_path() -> Path:
    """Pykis의 기본 작업공간 폴더를 반환합니다."""
    return (Path.home() / ".pykis").resolve()


def get_cache_path() -> Path:
    """Pykis의 캐시 폴더를 반환합니다."""
    return (get_workspace_path() / "cache").resolve()


def write_private_text(path: "str | Path", text: str) -> None:
    """소유자만 읽고 쓸 수 있는 권한(0600)으로 텍스트 파일을 저장합니다."""
    import os

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    try:
        # 이미 존재하던 파일의 권한도 제한합니다. (Windows 등에서는 무시될 수 있음)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except BaseException:
        # fdopen이 fd를 인수하기 전에 실패한 경우를 대비
        try:
            os.close(fd)
        except OSError:
            pass
        raise
