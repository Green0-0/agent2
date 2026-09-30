from __future__ import annotations
import json
import tomllib
from bisect import bisect_right
from pathlib import Path
from collections import OrderedDict

from agent2.core.objects import AgentConfig, Rollout
from agent2.code_parser.file import CodeFile, File
from agent2.code_parser.objects import CodeEdit, CodeState
from agent2.code_parser.languages.adapters import (
    get_adapter_for_extension,
    get_all_ignored_directories,
    get_all_ignored_extensions,
)

class Session:
    """
    Represents the global session state, including loaded configurations and active rollouts.
    Acts as the main registry and entrypoint before pipelines are executed.
    """
    def __init__(self, project_dir: str, config_dir: str = "config/agents", rollout_dir: str = ".agent2/task") -> None:
        """
        Initializes the Session by loading AgentConfigs from TOML files and existing Rollouts from JSON files.
        
        Args:
            project_dir (str): The root directory of the project.
            config_dir (str, optional): The directory containing agent TOML configs. Defaults to "config/agents".
            rollout_dir (str, optional): The directory containing JSON task rollouts. Defaults to ".agent2/task".
        """
        self.configs: OrderedDict[str, AgentConfig] = OrderedDict()
        self.datastore: OrderedDict[str, Rollout] = OrderedDict()
        self.files: OrderedDict[str, File] = OrderedDict()

        self.project_path = Path(project_dir).resolve()
        if not self.project_path.is_dir():
            raise ValueError(f"Project directory {self.project_path} does not exist or is not a directory")

        self.agent2_path = Path(__file__).resolve().parents[3]
        self.config_path = (self.agent2_path / config_dir).resolve()
        self.rollout_path = (self.project_path / rollout_dir).resolve()
        if not self.config_path.is_dir():
            raise ValueError(f"Config directory {self.config_path} does not exist or is not a directory")
        self.rollout_path.mkdir(parents=True, exist_ok=True)

        for file_path in sorted(self.config_path.glob("*.toml")):
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
                data["path"] = file_path.relative_to(self.agent2_path).as_posix()
                config = AgentConfig.model_validate(data)
                self.configs[config.path] = config
            
        for file_path in sorted(self.rollout_path.glob("*.json")):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                store = Rollout.model_validate(data)
                self.datastore[store.id] = store

        self.refresh_files()

    def refresh_files(self) -> None:
        """Reload changed disk files while retaining parsed objects for unchanged files."""
        found = set()
        ignored_dirs = get_all_ignored_directories()
        ignored_exts = get_all_ignored_extensions()
        for file_path in self.project_path.rglob("*"):
            relative = file_path.relative_to(self.project_path)
            if not file_path.is_file() or any(
                part.startswith(".") or part in ignored_dirs for part in relative.parts
            ) or file_path.suffix in ignored_exts:
                continue
            path = relative.as_posix()
            found.add(path)
            data = file_path.read_bytes()
            if path in self.files and self.files[path].current_state.bytes == data:
                continue
            adapter = get_adapter_for_extension(file_path.suffix)
            current = self.files.get(path)
            if isinstance(current, CodeFile) and current.adapter is adapter and current.tree:
                old = current.current_state.bytes
                start = next((i for i, pair in enumerate(zip(old, data)) if pair[0] != pair[1]), min(len(old), len(data)))
                old_end, new_end = len(old), len(data)
                while old_end > start and new_end > start and old[old_end - 1] == data[new_end - 1]:
                    old_end -= 1
                    new_end -= 1
                starts = current.current_state._line_starts
                start_row = bisect_right(starts, start) - 1
                end_row = bisect_right(starts, old_end) - 1
                try:
                    current.apply_edit_and_reparse(CodeEdit(
                        start, old_end,
                        (start_row, start - starts[start_row]),
                        (end_row, old_end - starts[end_row]),
                        data[start:new_end],
                    ))
                    current.original_state = current.current_state
                    continue
                except Exception:
                    pass
            if current and not adapter:
                current.original_state = current.current_state = CodeState(data)
            else:
                self.files[path] = CodeFile(path, adapter, data) if adapter else File(path, data)
        for path in self.files.keys() - found:
            del self.files[path]

    def get_config(self, config_path: str | Path) -> AgentConfig:
        """Look up a config by its stored path or an equivalent filesystem path."""
        path = (self.agent2_path / config_path).resolve()
        try:
            display_path = path.relative_to(self.agent2_path).as_posix()
        except ValueError:
            display_path = str(path)
        try:
            return self.configs[display_path]
        except KeyError as exc:
            raise KeyError(f"Agent config {display_path!r} is not loaded") from exc

    def register_rollout(self, rollout: Rollout) -> None:
        """Register a rollout and attach it to its parent, when present."""
        if rollout.id in self.datastore and self.datastore[rollout.id] is not rollout:
            raise ValueError(f"Rollout id {rollout.id!r} is already registered")
        parent = None
        if rollout.parent:
            try:
                parent = self.datastore[rollout.parent]
            except KeyError as exc:
                raise ValueError(f"Parent rollout {rollout.parent!r} is not registered") from exc
        self.datastore[rollout.id] = rollout
        if parent is not None:
            if rollout.id not in parent.children:
                parent.children.append(rollout.id)
                self.save_rollout(parent)

    def save_rollout(self, rollout: Rollout) -> Path:
        """Persist one rollout in the session's rollout directory."""
        self.datastore[rollout.id] = rollout
        destination = self.rollout_path / f"{rollout.id}.json"
        destination.write_text(rollout.model_dump_json(indent=2), encoding="utf-8")
        return destination
