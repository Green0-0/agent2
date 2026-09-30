from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agent2.code_parser.file import CodeFile, File
from agent2.code_parser.languages.adapters import get_adapter_for_extension
from agent2.code_parser.objects import CodeEdit, CodeState

if TYPE_CHECKING:
    from agent2.core.session import Session


class Workspace:
    """Files checked out from a session for shared or isolated agent work."""

    def __init__(self, session: Session):
        self.session = session
        self.files: dict[str, File] = {}

    @staticmethod
    def _file(path: str, data: bytes) -> File:
        adapter = get_adapter_for_extension(Path(path).suffix)
        return CodeFile(path, adapter, data) if adapter else File(path, data)

    def paths(self) -> set[str]:
        return (set(self.session.files) | set(self.files)) - {
            path for path, file in self.files.items() if file.current_state is None
        }

    def read_file(self, path: str) -> File | None:
        if path in self.files:
            return self.files[path] if self.files[path].current_state is not None else None
        return self.session.files.get(path)

    def _checkout(self, path: str) -> File | None:
        if path in self.files:
            return self.files[path] if self.files[path].current_state is not None else None
        source = self.session.files.get(path)
        if source is None:
            return None
        self.files[path] = self._file(path, source.current_state.bytes)
        self.files[path].original_state = source.current_state
        return self.files[path]

    def write_file(self, path: str, data: bytes) -> File:
        previous = self.files.get(path)
        current = self._checkout(path)
        original = (previous or current).original_state if previous or current else None
        self.files[path] = self._file(path, data)
        self.files[path].original_state = original
        return self.files[path]

    def apply_edit(self, path: str, edit: CodeEdit) -> File | None:
        file = self._checkout(path)
        if file is None:
            return None
        if isinstance(file, CodeFile):
            file.apply_edit_and_reparse(edit)
        else:
            data = file.current_state.bytes
            file.current_state = CodeState(data[:edit.start_byte] + edit.new_text + data[edit.end_byte:])
        return file

    def delete_file(self, path: str) -> bool:
        file = self._checkout(path)
        if file is None:
            return False
        file.current_state = None
        return True

    def clone(self) -> Workspace:
        workspace = Workspace(self.session)
        for path, file in self.files.items():
            copy = self._file(path, file.current_state.bytes) if file.current_state else File(path)
            copy.original_state = file.original_state
            workspace.files[path] = copy
        return workspace

    def commit(self) -> None:
        self.session.refresh_files()
        changes = {}
        conflicts = []
        for path, file in self.files.items():
            original = file.original_state.bytes if file.original_state else None
            current = file.current_state.bytes if file.current_state else None
            if current == original:
                continue
            live = self.session.files.get(path)
            live = live.current_state.bytes if live else None
            if live not in (original, current):
                conflicts.append(path)
            changes[path] = current
        if conflicts:
            raise ValueError(f"Stale workspace files: {', '.join(sorted(conflicts))}")
        for path, data in changes.items():
            destination = self.session.project_path / path
            if data is None:
                destination.unlink(missing_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
        self.session.refresh_files()
        self.files.clear()
