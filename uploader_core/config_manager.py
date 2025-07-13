import json
import os
import sys

class ConfigManager:
    def __init__(self):
        self.config_path = self._get_absolute_path('config/config.json')
        self.history_path = self._get_absolute_path('config/history.json')
        self.schedule_path = self._get_absolute_path('config/schedule.json')

        # Load configurations
        self.config = self._load_json(self.config_path, default={'ffmpeg_path': '', 'accounts': {}, 'settings': {}})
        self.history = self._load_json(self.history_path, default={'uploads': []})
        self.schedule = self._load_json(self.schedule_path, default={'tasks': []})

    def _get_absolute_path(self, relative_path):
        """Get the absolute path for a given relative path."""
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')
        return os.path.join(base_path, relative_path)

    def _load_json(self, file_path, default=None):
        """Load JSON data from a file, or return default if the file does not exist or is invalid."""
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            if default is not None:
                self.save_json(file_path, default)
                return default
            return None

    def save_json(self, file_path, data):
        """Save data to a JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_setting(self, key, default=None):
        """Get a setting value by key."""
        return self.config.get('settings', {}).get(key, default)

    def set_setting(self, key, value):
        """Set a setting value by key."""
        if 'settings' not in self.config:
            self.config['settings'] = {}
        self.config['settings'][key] = value
        self.save_json(self.config_path, self.config)

    def get_accounts(self):
        """Get the list of accounts."""
        return self.config.get('accounts', {})

    def add_account(self, account_name, credentials):
        """Add a new account with its credentials."""
        if 'accounts' not in self.config:
            self.config['accounts'] = {}
        self.config['accounts'][account_name] = credentials
        self.save_json(self.config_path, self.config)

    def remove_account(self, account_name):
        """Remove an account by name."""
        if 'accounts' in self.config and account_name in self.config['accounts']:
            del self.config['accounts'][account_name]
            self.save_json(self.config_path, self.config)

    def get_history(self):
        """Get the upload history."""
        return self.history.get('uploads', [])

    def add_history_entry(self, entry):
        """Add a new entry to the upload history."""
        if 'uploads' not in self.history:
            self.history['uploads'] = []
        self.history['uploads'].insert(0, entry)  # Insert at the beginning
        self.save_json(self.history_path, self.history)

    def get_schedule(self):
        """Get the scheduled tasks."""
        return self.schedule.get('tasks', [])

    def save_schedule(self, tasks):
        """Save the scheduled tasks."""
        self.schedule['tasks'] = tasks
        self.save_json(self.schedule_path, self.schedule)
