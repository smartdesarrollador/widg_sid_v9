"""
Global Search Panel Window - Independent window for searching all items across all categories
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent
from PyQt6.QtGui import QFont, QCursor
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.item import Item, ItemType
from views.widgets.item_widget import ItemButton
from views.widgets.search_bar import SearchBar
from views.advanced_filters_window import AdvancedFiltersWindow
from core.search_engine import SearchEngine
from core.advanced_filter_engine import AdvancedFilterEngine

# Get logger
logger = logging.getLogger(__name__)


class GlobalSearchPanel(QWidget):
    """Floating window for global search across all items"""

    # Signal emitted when an item is clicked
    item_clicked = pyqtSignal(object)

    # Signal emitted when window is closed
    window_closed = pyqtSignal()

    def __init__(self, db_manager=None, config_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.search_engine = SearchEngine()
        self.filter_engine = AdvancedFilterEngine()  # Motor de filtrado avanzado
        self.all_items = []  # Store all items before filtering
        self.current_filters = {}  # Filtros activos actuales

        # Get panel width from config
        if config_manager:
            self.panel_width = config_manager.get_setting('panel_width', 500)
        else:
            self.panel_width = 500

        # Resize handling
        self.resizing = False
        self.resize_start_x = 0
        self.resize_start_width = 0
        self.resize_edge_width = 15  # Width of the resize edge in pixels (increased)

        self.init_ui()

    def init_ui(self):
        """Initialize the floating panel UI"""
        # Window properties
        self.setWindowTitle("Widget Sidebar - Búsqueda Global")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        # Calculate window height: 80% of screen height (same as sidebar)
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_height = screen.availableGeometry().height()
            window_height = int(screen_height * 0.8)
        else:
            window_height = 600  # Fallback

        # Set window size (allow width to be resized)
        self.setMinimumWidth(300)  # Minimum width
        self.setMaximumWidth(1000)  # Maximum width
        self.setMinimumHeight(400)
        self.resize(self.panel_width, window_height)

        # Enable mouse tracking for resize cursor
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # Set window opacity
        self.setWindowOpacity(0.95)

        # Set background with different color for global search
        self.setStyleSheet("""
            GlobalSearchPanel {
                background-color: #252525;
                border: 2px solid #f093fb;
                border-left: 5px solid #f093fb;
                border-radius: 8px;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with title and close button
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f093fb,
                    stop:1 #f5576c
                );
                border-radius: 6px 6px 0 0;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 10, 10, 10)
        header_layout.setSpacing(5)

        # Title
        self.header_label = QLabel("🌐 Búsqueda Global")
        self.header_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #ffffff;
                font-size: 12pt;
                font-weight: bold;
            }
        """)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.header_label)

        # Close button
        close_button = QPushButton("✕")
        close_button.setFixedSize(24, 24)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                font-size: 12pt;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        close_button.clicked.connect(self.hide)
        header_layout.addWidget(close_button)

        main_layout.addWidget(header_widget)

        # Botón para abrir ventana de filtros avanzados
        filters_button_widget = QWidget()
        filters_button_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        filters_button_layout = QHBoxLayout(filters_button_widget)
        filters_button_layout.setContentsMargins(8, 5, 8, 5)
        filters_button_layout.setSpacing(0)

        self.open_filters_button = QPushButton("🔍 Filtros Avanzados")
        self.open_filters_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_filters_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f093fb,
                    stop:1 #f5576c
                );
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #df83eb,
                    stop:1 #e4475b
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ce73db,
                    stop:1 #d3374a
                );
            }
        """)
        self.open_filters_button.clicked.connect(self.toggle_filters_window)
        filters_button_layout.addWidget(self.open_filters_button)

        main_layout.addWidget(filters_button_widget)

        # Crear ventana flotante de filtros (oculta inicialmente)
        self.filters_window = AdvancedFiltersWindow(self)
        self.filters_window.filters_changed.connect(self.on_filters_changed)
        self.filters_window.filters_cleared.connect(self.on_filters_cleared)
        self.filters_window.hide()

        # Search bar
        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self.on_search_changed)
        main_layout.addWidget(self.search_bar)

        # Scroll area for items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #252525;
                border-radius: 0 0 6px 6px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
        """)

        # Container for items
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(0)
        self.items_layout.addStretch()

        scroll_area.setWidget(self.items_container)
        main_layout.addWidget(scroll_area)

    def load_all_items(self):
        """Load and display ALL items from ALL categories"""
        if not self.db_manager:
            logger.error("No database manager available")
            return

        logger.info("Loading all items for global search")

        # Get all items from database
        items_data = self.db_manager.get_all_items(include_inactive=False)

        # Convert dict items to Item objects
        self.all_items = []
        for item_dict in items_data:
            try:
                # Convert type string to ItemType enum (handle both uppercase and lowercase)
                type_str = item_dict['type'].lower() if item_dict['type'] else 'text'
                item_type = ItemType(type_str)

                item = Item(
                    item_id=str(item_dict['id']),
                    label=item_dict['label'],
                    content=item_dict['content'],
                    item_type=item_type,
                    icon=item_dict.get('icon'),
                    is_sensitive=bool(item_dict.get('is_sensitive', False)),
                    is_favorite=bool(item_dict.get('is_favorite', False)),
                    tags=item_dict.get('tags', []),
                    description=item_dict.get('description')
                )

                # Store category info for display
                item.category_name = item_dict.get('category_name', '')
                item.category_icon = item_dict.get('category_icon', '')
                item.category_color = item_dict.get('category_color', '')

                # Parse date fields from database (SQLite returns strings)
                from datetime import datetime
                if item_dict.get('created_at'):
                    try:
                        # SQLite datetime format: 'YYYY-MM-DD HH:MM:SS' or ISO format
                        created_at_str = item_dict['created_at']
                        if 'T' in created_at_str:
                            # ISO format
                            item.created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            # SQLite format
                            item.created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse created_at '{item_dict.get('created_at')}': {e}")
                        item.created_at = datetime.now()

                if item_dict.get('last_used'):
                    try:
                        last_used_str = item_dict['last_used']
                        if 'T' in last_used_str:
                            # ISO format
                            item.last_used = datetime.fromisoformat(last_used_str.replace('Z', '+00:00'))
                        else:
                            # SQLite format
                            item.last_used = datetime.strptime(last_used_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse last_used '{item_dict.get('last_used')}': {e}")
                        item.last_used = datetime.now()

                # Parse use_count
                item.use_count = item_dict.get('use_count', 0)

                self.all_items.append(item)
            except Exception as e:
                logger.error(f"Error converting item {item_dict.get('id')}: {e}")
                continue

        logger.info(f"Loaded {len(self.all_items)} items from database")

        # Update available tags in filters window
        self.filters_window.update_available_tags(self.all_items)
        logger.debug(f"Updated available tags from {len(self.all_items)} items")

        # Clear search bar
        self.search_bar.clear_search()

        # Display all items initially
        self.display_items(self.all_items)

        # Show the window
        self.show()
        self.raise_()
        self.activateWindow()

    def display_items(self, items):
        """Display a list of items"""
        logger.info(f"Displaying {len(items)} items")

        # Clear existing items
        self.clear_items()

        # Add items
        for idx, item in enumerate(items):
            logger.debug(f"Creating button {idx+1}/{len(items)}: {item.label}")
            item_button = ItemButton(item, show_category=True)  # show_category=True for global search
            item_button.item_clicked.connect(self.on_item_clicked)
            self.items_layout.insertWidget(self.items_layout.count() - 1, item_button)

        logger.info(f"Successfully added {len(items)} item buttons to layout")

    def clear_items(self):
        """Clear all item buttons"""
        while self.items_layout.count() > 1:  # Keep the stretch at the end
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_item_clicked(self, item: Item):
        """Handle item click"""
        # Emit signal to parent
        self.item_clicked.emit(item)

    def on_search_changed(self, query: str):
        """Handle search query change with filtering"""
        # Aplicar filtros avanzados primero
        filtered_items = self.filter_engine.apply_filters(self.all_items, self.current_filters)

        # Luego aplicar búsqueda si hay query
        if query and query.strip():
            # Search in labels, content, and tags
            search_results = []
            query_lower = query.lower()

            for item in filtered_items:
                # Search in label
                if query_lower in item.label.lower():
                    search_results.append(item)
                    continue

                # Search in content (if not sensitive)
                if not item.is_sensitive and query_lower in item.content.lower():
                    search_results.append(item)
                    continue

                # Search in tags
                if any(query_lower in tag.lower() for tag in item.tags):
                    search_results.append(item)
                    continue

                # Search in description
                if item.description and query_lower in item.description.lower():
                    search_results.append(item)
                    continue

            filtered_items = search_results

        self.display_items(filtered_items)

    def on_filters_changed(self, filters: dict):
        """Handle cuando cambian los filtros avanzados"""
        logger.info(f"Filters changed: {filters}")
        self.current_filters = filters

        # Re-aplicar búsqueda y filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

    def on_filters_cleared(self):
        """Handle cuando se limpian todos los filtros"""
        logger.info("All filters cleared")
        self.current_filters = {}

        # Re-aplicar búsqueda sin filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

    def position_near_sidebar(self, sidebar_window):
        """Position the floating panel near the sidebar window"""
        # Get sidebar window geometry
        sidebar_x = sidebar_window.x()
        sidebar_y = sidebar_window.y()
        sidebar_width = sidebar_window.width()

        # Position to the left of the sidebar
        panel_x = sidebar_x - self.width() - 10  # 10px gap
        panel_y = sidebar_y

        self.move(panel_x, panel_y)
        logger.debug(f"Positioned global search panel at ({panel_x}, {panel_y})")

    def is_on_left_edge(self, pos):
        """Check if mouse position is on the left edge for resizing"""
        return pos.x() <= self.resize_edge_width

    def event(self, event):
        """Override event to handle hover for cursor changes"""
        if event.type() == QEvent.Type.HoverMove:
            pos = event.position().toPoint()
            if self.is_on_left_edge(pos):
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        return super().event(event)

    def mousePressEvent(self, event):
        """Handle mouse press for dragging or resizing"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_on_left_edge(event.pos()):
                # Start resizing
                self.resizing = True
                self.resize_start_x = event.globalPosition().toPoint().x()
                self.resize_start_width = self.width()
                event.accept()
            else:
                # Start dragging
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging or resizing"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.resizing:
                # Calculate new width
                current_x = event.globalPosition().toPoint().x()
                delta_x = current_x - self.resize_start_x
                new_width = self.resize_start_width - delta_x  # Subtract because we're dragging from left edge

                # Apply constraints
                new_width = max(self.minimumWidth(), min(new_width, self.maximumWidth()))

                # Resize and reposition
                old_width = self.width()
                old_x = self.x()
                self.resize(new_width, self.height())

                # Adjust position to keep right edge fixed
                width_diff = self.width() - old_width
                self.move(old_x - width_diff, self.y())

                event.accept()
            else:
                # Dragging
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end resizing"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resizing:
                self.resizing = False
                # Save new width to config
                if self.config_manager:
                    self.config_manager.set_setting('panel_width', self.width())
                event.accept()

    def toggle_filters_window(self):
        """Abrir/cerrar la ventana de filtros avanzados"""
        if self.filters_window.isVisible():
            self.filters_window.hide()
        else:
            # Posicionar cerca del panel flotante
            self.filters_window.position_near_panel(self)
            self.filters_window.show()
            self.filters_window.raise_()
            self.filters_window.activateWindow()

    def closeEvent(self, event):
        """Handle window close event"""
        # Cerrar también la ventana de filtros si está abierta
        if self.filters_window.isVisible():
            self.filters_window.close()

        self.window_closed.emit()
        event.accept()
