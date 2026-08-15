import json
import tomllib
from pathlib import Path
from collections import OrderedDict
from agent2.agent import AgentConfig, Rollout

class Session:
    def __init__(self, config_dir: str = "config/agents", rollout_dir: str = ".agent2/task") -> None:
        self.configs: OrderedDict[str, AgentConfig] = OrderedDict()
        self.datastore: OrderedDict[str, Rollout] = OrderedDict()
        
        config_path = Path(config_dir)
        rollout_path = Path(rollout_dir)
        assert config_path.exists() and config_path.is_dir(), f"Config directory {config_path} does not exist or is not a directory" 
        assert rollout_path.exists() and rollout_path.is_dir(), f"Rollout directory {rollout_path} does not exist or is not a directory" 

        for file_path in config_path.glob("*.toml"):
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
                config = AgentConfig.model_validate(data)
                self.configs[config.id] = config
            
        for file_path in rollout_path.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                store = Rollout.model_validate(data)
                self.datastore[store.agent_id] = store