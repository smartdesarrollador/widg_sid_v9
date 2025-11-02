"""
Settings Window
Main settings dialog with tabbed interface
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import sys
import logging
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from views.category_editor import CategoryEditor
from views.appearance_settings import AppearanceSettings
from views.hotkey_settings import HotkeySettings
from views.general_settings import GeneralSettings
from views.browser_settings import BrowserSettings

# Get logger
logger = logging.getLogger(__name__)


class SettingsWindow(QDialog):
    """
    Settings window with tabbed interface
    Modal dialog for configuring all application settings
    """

    # Signal emitted when settings are saved
    settings_changed = pyqtSignal()

    def __init__(self, controller=None, parent=None):
        """
        Initialize settings window

        Args:
            controller: MainController instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.controller = controller
        self.config_manager = controller.config_manager if controller else None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the UI"""
        # Window properties
        self.setWindowTitle("Configuración")
        self.setFixedSize(600, 650)
        self.setModal(True)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #252525;
                color: #cccccc;
                padding: 10px 20px;
                margin-right: 2px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                color: #ffffff;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d2d2d;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #007acc;
            }
            QPushButton#save_button {
                background-color: #007acc;
                color: #ffffff;
                border: none;
            }
            QPushButton#save_button:hover {
                background-color: #005a9e;
            }
            QPushButton#apply_button {
                background-color: #0e6b0e;
                color: #ffffff;
                border: none;
            }
            QPushButton#apply_button:hover {
                background-color: #0a520a;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self.category_editor = CategoryEditor(controller=self.controller)
        self.appearance_settings = AppearanceSettings(config_manager=self.config_manager)
        self.hotkey_settings = HotkeySettings(config_manager=self.config_manager)
        self.browser_settings = BrowserSettings(controller=self.controller)
        self.general_settings = GeneralSettings(config_manager=self.config_manager)

        # Add tabs
        self.tab_widget.addTab(self.category_editor, "Categorías")
        self.tab_widget.addTab(self.appearance_settings, "Apariencia")
        self.tab_widget.addTab(self.hotkey_settings, "Hotkeys")
        self.tab_widget.addTab(self.browser_settings, "Navegador")
        self.tab_widget.addTab(self.general_settings, "General")

        main_layout.addWidget(self.tab_widget)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Cancel button
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        buttons_layout.addStretch()

        # Apply button
        self.apply_button = QPushButton("Aplicar")
        self.apply_button.setObjectName("apply_button")
        self.apply_button.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(self.apply_button)

        # Save button
        self.save_button = QPushButton("Guardar")
        self.save_button.setObjectName("save_button")
        self.save_button.clicked.connect(self.save_settings)
        buttons_layout.addWidget(self.save_button)

        main_layout.addLayout(buttons_layout)

    def load_settings(self):
        """Load current settings into all tabs"""
        # Category editor loads its own data
        self.category_editor.load_categories()

        # Other tabs load through their __init__ methods
        # Already done in init_ui

    def apply_settings(self):
        """Apply settings without closing dialog"""
        try:
            # Save current category name to restore selection after reload
            current_category_name = None
            if self.category_editor.current_category:
                current_category_name = self.category_editor.current_category.name
                logger.info(f"[APPLY] Current category before save: {current_category_name}")

            # Save to config
            if self.save_to_config():
                # DO NOT reload categories here! This would lose new categories in memory
                # that haven't been saved yet. Only reload after final save_settings().
                logger.info("[APPLY] Categories saved successfully (NOT reloading to preserve new categories in memory)")
                logger.info(f"[APPLY] Current categories in editor: {len(self.category_editor.categories)}")

                # Restore previous selection by category name
                if current_category_name:
                    logger.info(f"[APPLY] Restoring selection for: {current_category_name}")
                    for i in range(self.category_editor.categories_list.count()):
                        item = self.category_editor.categories_list.item(i)
                        category = item.data(Qt.ItemDataRole.UserRole)
                        if category.name == current_category_name:
                            logger.info(f"[APPLY] Found category at index {i}, setting as current")
                            self.category_editor.categories_list.setCurrentItem(item)
                            # Force update current_category
                            self.category_editor.current_category = category
                            logger.info(f"[APPLY] Current category updated, has {len(category.items)} items")
                            self.category_editor.refresh_items_list()
                            break

                QMessageBox.information(
                    self,
                    "Aplicar Configuración",
                    "Configuración aplicada correctamente.\n\n"
                    "Algunos cambios requieren reiniciar la aplicación."
                )
                self.settings_changed.emit()
        except Exception as e:
            logger.error(f"[APPLY] Error: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al aplicar configuración:\n{str(e)}"
            )

    def save_settings(self):
        """Save all settings and close dialog"""
        try:
            logger.info("=== SAVE_SETTINGS CALLED ===")
            logger.info("Attempting to save settings...")

            if self.save_to_config():
                logger.info("Settings saved successfully")
                # Reload categories to sync IDs from database
                # (This is important for newly created categories)
                logger.info("Reloading categories to sync with database...")
                self.category_editor.load_categories()
                logger.info("Categories reloaded successfully")
                self.settings_changed.emit()
                logger.info("Settings changed signal emitted")
                self.accept()
                logger.info("Dialog accepted")
            else:
                logger.error("save_to_config returned False")
                QMessageBox.warning(
                    self,
                    "Advertencia",
                    "No se pudieron guardar algunos ajustes"
                )

        except Exception as e:
            logger.critical(f"CRITICAL ERROR in save_settings: {e}", exc_info=True)

            QMessageBox.critical(
                self,
                "Error",
                f"Se produjo un error al guardar:\n{str(e)}\n\nRevisa widget_sidebar_error.log para más detalles."
            )

    def save_to_config(self) -> bool:
        """
        Save all settings to config manager

        Returns:
            True if successful
        """
        try:
            logger.info("=== SAVE_TO_CONFIG CALLED ===")

            if not self.config_manager:
                logger.error("No config_manager available")
                return False

            # Get settings from all tabs
            logger.info("Getting settings from tabs...")
            appearance_settings = self.appearance_settings.get_settings()
            logger.debug(f"Appearance settings: {appearance_settings}")

            hotkey_settings = self.hotkey_settings.get_settings()
            logger.debug(f"Hotkey settings: {hotkey_settings}")

            general_settings = self.general_settings.get_settings()
            logger.debug(f"General settings: {general_settings}")

            # Update config
            logger.info("Updating config settings...")
            self.config_manager.set_setting("theme", appearance_settings["theme"])
            self.config_manager.set_setting("opacity", appearance_settings["opacity"])
            self.config_manager.set_setting("sidebar_width", appearance_settings["sidebar_width"])
            self.config_manager.set_setting("panel_width", appearance_settings["panel_width"])
            self.config_manager.set_setting("animation_speed", appearance_settings["animation_speed"])
            logger.debug("Appearance settings saved")

            self.config_manager.set_setting("hotkey", hotkey_settings["hotkey"])
            logger.debug("Hotkey settings saved")

            self.config_manager.set_setting("minimize_to_tray", general_settings["minimize_to_tray"])
            self.config_manager.set_setting("always_on_top", general_settings["always_on_top"])
            self.config_manager.set_setting("start_with_windows", general_settings["start_with_windows"])
            self.config_manager.set_setting("max_history", general_settings["max_history"])
            logger.debug("General settings saved")

            # Save categories
            logger.info("Saving categories...")
            categories = self.category_editor.get_categories()
            logger.info(f"Got {len(categories)} categories from editor")

            if self.controller:
                # Update controller's categories
                logger.debug("Updating controller categories...")
                self.controller.categories = categories

                # Get existing categories from database to avoid duplicates
                existing_categories = self.config_manager.get_categories()
                existing_ids = {cat.id: cat for cat in existing_categories}
                existing_names = {cat.name: cat for cat in existing_categories}

                # Track which categories are in the editor (to detect deletions)
                current_category_ids = set()
                current_category_names = set()

                # Save each category to database through config_manager
                logger.info("Saving categories to database...")
                for i, category in enumerate(categories):
                    logger.info(f"[SAVE] Processing category {i+1}/{len(categories)}: '{category.name}' (ID: '{category.id}')")
                    logger.info(f"[SAVE]   - Category has {len(category.items)} items")
                    logger.info(f"[SAVE]   - order_index: {category.order_index}")
                    logger.info(f"[SAVE]   - is_active: {category.is_active}")
                    logger.info(f"[SAVE]   - is_predefined: {category.is_predefined}")

                    for idx, item in enumerate(category.items):
                        logger.info(f"[SAVE]     Item {idx+1}: {item.label} (ID: {item.id})")

                    logger.debug(f"[SAVE]   - ID is digit: {category.id.isdigit()}")
                    logger.debug(f"[SAVE]   - ID in existing_ids: {category.id in existing_ids}")
                    logger.debug(f"[SAVE]   - Name in existing_names: {category.name in existing_names}")

                    # Track this category
                    current_category_names.add(category.name)
                    if category.id.isdigit():
                        current_category_ids.add(category.id)

                    # Check if category exists by ID (numeric) or by name
                    if category.id.isdigit() and category.id in existing_ids:
                        logger.info(f"[SAVE] → Updating existing category by ID: {category.id}")
                        result = self.config_manager.update_category(category.id, category)
                        logger.info(f"[SAVE]   Update result: {result}")
                    elif category.name in existing_names:
                        # Category exists with this name - update it
                        existing_cat = existing_names[category.name]
                        logger.info(f"[SAVE] → Updating existing category by name: '{category.name}' (ID: {existing_cat.id})")
                        result = self.config_manager.update_category(existing_cat.id, category)
                        logger.info(f"[SAVE]   Update result: {result}")
                        # Track the actual ID from database
                        current_category_ids.add(existing_cat.id)
                    else:
                        logger.info(f"[SAVE] → This is a NEW CATEGORY! '{category.name}' (ID: '{category.id}')")
                        logger.info(f"[SAVE]   Calling config_manager.add_category()...")
                        logger.info(f"[SAVE]   Category validation: {category.validate()}")
                        result = self.config_manager.add_category(category)
                        logger.info(f"[SAVE]   Add result: {result}")
                        if not result:
                            logger.error(f"[SAVE]   ❌ FAILED to add category '{category.name}'!")
                        else:
                            logger.info(f"[SAVE]   ✅ Category '{category.name}' added successfully")

                # Delete categories that were removed from the editor
                logger.info("Checking for deleted categories...")
                for existing_cat in existing_categories:
                    if existing_cat.id not in current_category_ids and existing_cat.name not in current_category_names:
                        logger.info(f"→ Deleting removed category: '{existing_cat.name}' (ID: {existing_cat.id})")
                        result = self.config_manager.delete_category(existing_cat.id)
                        logger.info(f"  Delete result: {result}")

                logger.info(f"Categories saved successfully: {len(categories)} categories")

            logger.info("=== SAVE_TO_CONFIG COMPLETED SUCCESSFULLY ===")
            return True

        except Exception as e:
            logger.critical(f"CRITICAL ERROR in save_to_config: {e}", exc_info=True)
            raise

    def closeEvent(self, event):
        """Override close event to check for unsaved changes"""
        # For now, just accept the close
        # TODO: Add unsaved changes detection
        event.accept()
