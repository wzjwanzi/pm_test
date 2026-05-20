"""Local JSON persistence for saved desktop cases."""
from __future__ import annotations

import json
import re
from pathlib import Path

import config
from desktop.case_models import CaseStep, SavedCase, now_iso


_WINDOWS_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SAFE_NAME_MAX_LENGTH = 80


def _safe_filename_part(name: str) -> str:
    cleaned = _WINDOWS_INVALID_CHARS.sub("_", name.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned.strip(" ._")
    if not cleaned:
        return "case"
    return cleaned[:_SAFE_NAME_MAX_LENGTH].rstrip(" ._") or "case"


class CaseLibrary:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path(config.CASES_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def list_cases(self) -> list[SavedCase]:
        cases: list[SavedCase] = []
        for path in self.root.glob("*.json"):
            try:
                cases.append(self._read(path))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        return sorted(cases, key=lambda item: (item.name, item.case_id))

    def save(self, case: SavedCase) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(case)
        self._write(path, case)
        return path

    def load(self, filename_or_case_id: str) -> SavedCase:
        return self._read(self._find_path(filename_or_case_id))

    def rename(self, case_id: str, name: str) -> SavedCase:
        old_path = self._find_path(case_id)
        case = self._read(old_path)
        case.name = name
        case.updated_at = now_iso()

        new_path = self._path_for(case)
        self._write(new_path, case)
        if new_path != old_path:
            old_path.unlink()
        return case

    def copy_case(self, case_id: str, name: str) -> SavedCase:
        source = self.load(case_id)
        copied_steps = [
            CaseStep.from_dict(step.to_dict())
            for step in source.steps
        ]
        copied = SavedCase.new(name, copied_steps, source.description)
        self.save(copied)
        return copied

    def delete(self, case_id: str) -> None:
        self._find_path(case_id).unlink()

    def _path_for(self, case: SavedCase) -> Path:
        safe_name = _safe_filename_part(case.name)
        return self.root / f"{safe_name}-{case.case_id}.json"

    def _find_path(self, filename_or_case_id: str) -> Path:
        candidate = Path(filename_or_case_id)
        if candidate.name != filename_or_case_id:
            candidate = candidate.name

        named_path = self.root / str(candidate)
        if named_path.suffix.lower() == ".json" and named_path.exists():
            return named_path

        for path in self.root.glob("*.json"):
            try:
                case = self._read(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if case.case_id == filename_or_case_id:
                return path

        raise FileNotFoundError(f"Saved case not found: {filename_or_case_id}")

    def _read(self, path: Path) -> SavedCase:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Saved case JSON must be an object: {path}")
        if data.get("moved_to"):
            raise ValueError(f"Saved case moved: {path}")
        return SavedCase.from_dict(data)

    def _write(self, path: Path, case: SavedCase) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(case.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
