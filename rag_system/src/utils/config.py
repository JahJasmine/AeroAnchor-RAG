import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Load the shared root .env (project root) so API keys are set once for
        # every service. Env vars are read by llm_client with config.yaml as fallback.
        root_env = Path(__file__).parent.parent.parent.parent / ".env"
        load_dotenv(dotenv_path=root_env, override=False)
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

config = Config()