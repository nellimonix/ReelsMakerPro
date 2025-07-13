import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QMessageBox, QInputDialog, QFileDialog, 
                             QLineEdit, QDialog, QFormLayout)
from PyQt5.QtCore import Qt
import qtawesome as qta
from uploader_core.config_manager import ConfigManager
from uploader_core.auth_manager import AuthManager
from uploader_ui.account_tab_widget import AccountTabWidget


class UploaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.auth_manager = AuthManager(self.config_manager)
        
        # Initialize account tabs dictionary
        self.account_tabs = {}
        
        # Setup UI and load accounts
        self._setup_ui()
        self._load_accounts()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create top bar layout
        top_bar_layout = QHBoxLayout()
        
        # Add account button
        self.add_account_btn = QPushButton('Добавить аккаунт')
        self.add_account_btn.setIcon(qta.icon('fa5s.plus-circle', color='white', color_active='white'))
        self.add_account_btn.clicked.connect(self._add_account_handler)
        
        top_bar_layout.addWidget(self.add_account_btn)
        top_bar_layout.addStretch()
        
        # Add top bar to main layout
        self.main_layout.addLayout(top_bar_layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab_handler)
        
        # Add tabs widget to main layout
        self.main_layout.addWidget(self.tabs)
    
    def _load_accounts(self):
        """Load existing accounts from configuration"""
        accounts = self.config_manager.get_accounts()
        for account_name in accounts.keys():
            self._create_account_tab(account_name)
    
    def _add_account_handler(self):
        """Handle adding a new account"""
        # Get account name from user
        account_name, ok = QInputDialog.getText(
            self, 
            'Добавить аккаунт',
            'Введите имя для этого аккаунта (например, "Личный блог"):'
        )
        
        if not ok or not account_name:
            return
        
        # Check if account already exists
        if account_name in self.config_manager.get_accounts():
            QMessageBox.warning(
                self,
                'Ошибка',
                'Аккаунт с таким именем уже существует.'
            )
            return
        
        # Check if client secrets directory exists and is not empty
        client_secrets_path = os.path.join('config', 'client_secrets')
        if not os.path.exists(client_secrets_path) or not os.listdir(client_secrets_path):
            QMessageBox.critical(
                self,
                'Ошибка',
                "Папка 'config/client_secrets' пуста. Поместите в нее ваш JSON файл с ключами API Google."
            )
            return
        
        # Get the first secrets file
        secrets_file = os.path.join(
            client_secrets_path,
            os.listdir(client_secrets_path)[0]
        )
        
        # Authenticate the account
        self.auth_manager.authenticate(account_name, secrets_file)
        
        # Check if authentication was successful
        if self.auth_manager.get_credentials(account_name):
            QMessageBox.information(
                self,
                'Успех',
                f"Аккаунт '{account_name}' успешно добавлен."
            )
            self._create_account_tab(account_name)
        else:
            QMessageBox.critical(
                self,
                'Ошибка',
                f"Не удалось аутентифицировать аккаунт '{account_name}'."
            )
    
    def _create_account_tab(self, account_name):
        """Create a new account tab"""
        # Check if tab already exists
        if account_name in self.account_tabs:
            return
        
        # Create new tab widget
        tab_widget = AccountTabWidget(
            account_name,
            self.config_manager,
            self.auth_manager
        )
        
        # Create icon for tab
        icon = qta.icon('fa5s.user-circle', color='white', color_active='white')
        
        # Add tab to tab widget
        index = self.tabs.addTab(tab_widget, icon, f' {account_name} ')
        self.tabs.setCurrentIndex(index)
        
        # Store tab widget reference
        self.account_tabs[account_name] = tab_widget
    
    def _close_tab_handler(self, index):
        """Handle tab close request"""
        # Get the tab widget and account name
        tab_widget = self.tabs.widget(index)
        account_name = tab_widget.account_name
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            'Удалить аккаунт',
            f"Вы уверены, что хотите удалить аккаунт '{account_name}'? Это действие необратимо.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove account from configuration
            self.config_manager.remove_account(account_name)
            
            # Remove credentials
            self.auth_manager.remove_credentials(account_name)
            
            # Remove tab
            self.tabs.removeTab(index)
            
            # Remove from account tabs dictionary
            if account_name in self.account_tabs:
                del self.account_tabs[account_name]
    
    def get_account_names(self):
        """Get list of account names"""
        return list(self.config_manager.get_accounts().keys())
    
    def receive_video_for_upload(self, video_path, account_name):
        """Receive video for upload to specific account"""
        if account_name in self.account_tabs:
            # Switch to the account tab
            self.tabs.setCurrentWidget(self.account_tabs[account_name])
            
            # Get the account widget
            account_widget = self.account_tabs[account_name]
            
            # Set the upload tab as current (index 0)
            account_widget.sub_tabs.setCurrentIndex(0)
            
            # Set the video path in the form
            account_widget.video_path_edit.setText(video_path)
            
            # Show success message
            QMessageBox.information(
                self,
                'Видео готово',
                f"Видео добавлено в форму загрузки для аккаунта '{account_name}'."
            )
        else:
            # Show error message
            QMessageBox.warning(
                self,
                'Ошибка',
                f"Не найден виджет для аккаунта '{account_name}'."
            )