import json
import os

class ConfigManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_path = os.path.join(self.base_dir, "data")

    def load_json(self, filename):
        full_path = os.path.join(self.data_path, filename)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_json(self, filename, data):
        full_path = os.path.join(self.data_path, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)