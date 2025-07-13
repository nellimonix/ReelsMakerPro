import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class AuthManager:
    """Менеджер аутентификации для Google API"""
    
    def __init__(self, config_manager):
        """Инициализация менеджера аутентификации"""
        self.config_manager = config_manager
        self.credentials_dir = self._get_absolute_path('config/credentials')
        
        # Создаем директорию для хранения учетных данных если её нет
        if not os.path.exists(self.credentials_dir):
            os.makedirs(self.credentials_dir)
    
    def _get_absolute_path(self, relative_path):
        """Получить абсолютный путь (поддержка PyInstaller)"""
        import sys
        
        # Проверяем, запущено ли приложение из PyInstaller
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')
        
        return os.path.join(base_path, relative_path)
    
    def _get_credential_path(self, account_name):
        """Получить путь к файлу с учетными данными для аккаунта"""
        return os.path.join(self.credentials_dir, f'{account_name}.pickle')
    
    def authenticate(self, account_name, client_secrets_file, 
                    scopes=['https://www.googleapis.com/auth/youtube.upload']):
        """Аутентификация аккаунта YouTube"""
        creds = None
        credential_path = self._get_credential_path(account_name)
        
        # Пытаемся загрузить существующие учетные данные
        if os.path.exists(credential_path):
            try:
                with open(credential_path, 'rb') as token:
                    creds = pickle.load(token)
            except:
                pass
        
        # Проверяем валидность учетных данных
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Обновляем токен
                creds.refresh(Request())
            else:
                # Выполняем первичную аутентификацию
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, scopes)
                creds = flow.run_local_server(port=0)
        
        # Сохраняем учетные данные
        with open(credential_path, 'wb') as token:
            pickle.dump(creds, token)
        
        # Добавляем аккаунт в конфигурацию
        self.config_manager.add_account(account_name, credential_path)
        
        return creds
    
    def get_credentials(self, account_name):
        """Получить учетные данные для аккаунта"""
        # Проверяем, есть ли аккаунт в конфигурации
        account_info = self.config_manager.get_accounts().get(account_name)
        if not account_info:
            return None
        
        credential_path = self._get_credential_path(account_name)
        creds = None
        
        # Загружаем сохраненные учетные данные
        if os.path.exists(credential_path):
            try:
                with open(credential_path, 'rb') as token:
                    creds = pickle.load(token)
            except:
                pass
        
        # Проверяем и обновляем токен при необходимости
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Сохраняем обновленные учетные данные
            with open(credential_path, 'wb') as token:
                pickle.dump(creds, token)
            return creds
        
        return creds
    
    def remove_credentials(self, account_name):
        """Удалить учетные данные аккаунта"""
        credential_path = self._get_credential_path(account_name)
        
        if os.path.exists(credential_path):
            os.remove(credential_path)