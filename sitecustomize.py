from pathlib import Path
import sys

_repo_root = Path(__file__).resolve().parent
_src = _repo_root / "src"
if _src.exists():
    src_text = str(_src)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)
