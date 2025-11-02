"""
Database Manager for Widget Sidebar
Manages SQLite database operations for settings, categories, items, and clipboard history
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DBManager:
    """Gestor de base de datos SQLite para Widget Sidebar"""

    def __init__(self, db_path: str = "widget_sidebar.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._ensure_database()
        logger.info(f"Database initialized at: {self.db_path}")

    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        # Check if it's an in-memory database or file doesn't exist
        is_memory_db = str(self.db_path) == ":memory:"
        if is_memory_db or not self.db_path.exists():
            logger.info("Creating new database...")
            self._create_database()
        else:
            logger.info("Database already exists")

    def connect(self) -> sqlite3.Connection:
        """
        Establish connection to the database

        Returns:
            sqlite3.Connection: Database connection
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions

        Usage:
            with db.transaction() as conn:
                conn.execute(...)
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def _create_database(self):
        """Create database schema with all tables and indices"""
        # Use self.connect() to ensure we use the same connection (important for :memory:)
        conn = self.connect()
        cursor = conn.cursor()

        # Create tables
        cursor.executescript("""
            -- Tabla de configuración general
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Tabla de categorías
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT,
                order_index INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_predefined BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                color TEXT,
                badge TEXT,
                item_count INTEGER DEFAULT 0,
                total_uses INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                is_pinned BOOLEAN DEFAULT 0,
                pinned_order INTEGER DEFAULT 0
            );

            -- Tabla de items
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT CHECK(type IN ('TEXT', 'URL', 'CODE', 'PATH')) DEFAULT 'TEXT',
                icon TEXT,
                is_sensitive BOOLEAN DEFAULT 0,
                is_favorite BOOLEAN DEFAULT 0,
                favorite_order INTEGER DEFAULT 0,
                use_count INTEGER DEFAULT 0,
                tags TEXT,
                description TEXT,
                working_dir TEXT,
                color TEXT,
                badge TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_archived BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                -- Campos de listas avanzadas
                is_list BOOLEAN DEFAULT 0,
                list_group TEXT DEFAULT NULL,
                orden_lista INTEGER DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );

            -- Tabla de historial de portapapeles
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                content TEXT NOT NULL,
                copied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
            );

            -- Tabla de paneles anclados (pinned panels)
            CREATE TABLE IF NOT EXISTS pinned_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                custom_name TEXT,
                custom_color TEXT,
                x_position INTEGER NOT NULL,
                y_position INTEGER NOT NULL,
                width INTEGER NOT NULL DEFAULT 350,
                height INTEGER NOT NULL DEFAULT 500,
                is_minimized BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                open_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );

            -- Tabla de configuración del navegador embebido
            CREATE TABLE IF NOT EXISTS browser_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_url TEXT DEFAULT 'https://www.google.com',
                is_visible BOOLEAN DEFAULT 0,
                width INTEGER DEFAULT 500,
                height INTEGER DEFAULT 700,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Índices para optimización
            CREATE INDEX IF NOT EXISTS idx_categories_order ON categories(order_index);
            CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
            CREATE INDEX IF NOT EXISTS idx_items_last_used ON items(last_used DESC);
            CREATE INDEX IF NOT EXISTS idx_clipboard_history_date ON clipboard_history(copied_at DESC);
            CREATE INDEX IF NOT EXISTS idx_pinned_category ON pinned_panels(category_id);
            CREATE INDEX IF NOT EXISTS idx_pinned_last_opened ON pinned_panels(last_opened DESC);
            CREATE INDEX IF NOT EXISTS idx_pinned_active ON pinned_panels(is_active);
            -- Índices para listas avanzadas
            CREATE INDEX IF NOT EXISTS idx_items_is_list ON items(is_list) WHERE is_list = 1;
            CREATE INDEX IF NOT EXISTS idx_items_list_group ON items(list_group) WHERE list_group IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_items_orden_lista ON items(category_id, list_group, orden_lista) WHERE is_list = 1;

            -- Configuración inicial por defecto
            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('theme', '"dark"'),
                ('panel_width', '300'),
                ('sidebar_width', '70'),
                ('hotkey', '"ctrl+shift+v"'),
                ('always_on_top', 'true'),
                ('start_with_windows', 'false'),
                ('animation_speed', '300'),
                ('opacity', '0.95'),
                ('max_history', '20');
        """)

        conn.commit()
        # Don't close the connection - it's managed by self.connection
        logger.info("Database schema created successfully")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Execute SELECT query and return results as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            List[Dict]: Query results
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute INSERT/UPDATE/DELETE query

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            int: Last row ID for INSERT, or number of affected rows
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Update execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute multiple INSERT queries in a single transaction

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
            logger.info(f"Batch execution completed: {len(params_list)} rows")
        except sqlite3.Error as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    # ========== SETTINGS ==========

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get configuration setting by key

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Any: Setting value (parsed from JSON)
        """
        query = "SELECT value FROM settings WHERE key = ?"
        result = self.execute_query(query, (key,))
        if result:
            try:
                return json.loads(result[0]['value'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse setting '{key}': {e}")
                return default
        return default

    def set_setting(self, key: str, value: Any) -> None:
        """
        Save or update configuration setting

        Args:
            key: Setting key
            value: Setting value (will be JSON encoded)
        """
        value_json = json.dumps(value)
        query = """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """
        self.execute_update(query, (key, value_json))
        logger.debug(f"Setting saved: {key} = {value}")

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all configuration settings

        Returns:
            Dict[str, Any]: Dictionary of all settings
        """
        query = "SELECT key, value FROM settings"
        results = self.execute_query(query)
        settings = {}
        for row in results:
            try:
                settings[row['key']] = json.loads(row['value'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse setting '{row['key']}': {e}")
        return settings

    # ========== CATEGORIES ==========

    def get_categories(self, include_inactive: bool = False) -> List[Dict]:
        """
        Get all categories ordered by order_index

        Args:
            include_inactive: Include inactive categories

        Returns:
            List[Dict]: List of category dictionaries
        """
        query = """
            SELECT * FROM categories
            WHERE is_active = 1 OR ? = 1
            ORDER BY order_index
        """
        return self.execute_query(query, (include_inactive,))

    def get_category(self, category_id: int) -> Optional[Dict]:
        """
        Get category by ID

        Args:
            category_id: Category ID

        Returns:
            Optional[Dict]: Category dictionary or None
        """
        query = "SELECT * FROM categories WHERE id = ?"
        result = self.execute_query(query, (category_id,))
        return result[0] if result else None

    def add_category(self, name: str, icon: str = None,
                     is_predefined: bool = False, order_index: int = None) -> int:
        """
        Add new category

        Args:
            name: Category name
            icon: Category icon (optional)
            is_predefined: Whether this is a predefined category
            order_index: Order index (optional, will auto-calculate if None)

        Returns:
            int: New category ID
        """
        # Use provided order_index or calculate next one
        if order_index is None:
            max_order = self.execute_query(
                "SELECT MAX(order_index) as max_order FROM categories"
            )
            order_index = (max_order[0]['max_order'] or 0) + 1

        query = """
            INSERT INTO categories (name, icon, order_index, is_predefined, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        category_id = self.execute_update(query, (name, icon, order_index, is_predefined))
        logger.info(f"Category added: {name} (ID: {category_id}, order_index: {order_index})")
        return category_id

    def update_category(self, category_id: int, name: str = None,
                        icon: str = None, order_index: int = None,
                        is_active: bool = None) -> None:
        """
        Update category fields

        Args:
            category_id: Category ID to update
            name: New name (optional)
            icon: New icon (optional)
            order_index: New order (optional)
            is_active: New active status (optional)
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if order_index is not None:
            updates.append("order_index = ?")
            params.append(order_index)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(category_id)
            query = f"UPDATE categories SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Category updated: ID {category_id}")

    def delete_category(self, category_id: int) -> None:
        """
        Delete category (cascade deletes all items)

        Args:
            category_id: Category ID to delete
        """
        query = "DELETE FROM categories WHERE id = ?"
        self.execute_update(query, (category_id,))
        logger.info(f"Category deleted: ID {category_id}")

    def reorder_categories(self, category_ids: List[int]) -> None:
        """
        Reorder categories by providing ordered list of IDs

        Args:
            category_ids: List of category IDs in desired order
        """
        updates = [(i, cat_id) for i, cat_id in enumerate(category_ids)]
        query = "UPDATE categories SET order_index = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_many(query, updates)
        logger.info(f"Categories reordered: {len(category_ids)} items")

    # ========== ITEMS ==========

    def get_items_by_category(self, category_id: int) -> List[Dict]:
        """
        Get all items for a specific category

        Args:
            category_id: Category ID

        Returns:
            List[Dict]: List of item dictionaries (content decrypted if sensitive)
        """
        query = """
            SELECT * FROM items
            WHERE category_id = ?
            ORDER BY created_at
        """
        results = self.execute_query(query, (category_id,))

        # Initialize encryption manager for decrypting sensitive items
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        # Parse tags and decrypt sensitive content
        for item in results:
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        return results

    def get_item(self, item_id: int) -> Optional[Dict]:
        """
        Get item by ID

        Args:
            item_id: Item ID

        Returns:
            Optional[Dict]: Item dictionary or None (content decrypted if sensitive)
        """
        query = "SELECT * FROM items WHERE id = ?"
        result = self.execute_query(query, (item_id,))
        if result:
            item = result[0]
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                from core.encryption_manager import EncryptionManager
                encryption_manager = EncryptionManager()
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item_id}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item_id}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

            return item
        return None

    def add_item(self, category_id: int, label: str, content: str,
                 item_type: str = 'TEXT', icon: str = None,
                 is_sensitive: bool = False, is_favorite: bool = False,
                 tags: List[str] = None, description: str = None,
                 working_dir: str = None, color: str = None,
                 is_active: bool = True, is_archived: bool = False,
                 is_list: bool = False, list_group: str = None,
                 orden_lista: int = 0) -> int:
        """
        Add new item to category

        Args:
            category_id: Category ID
            label: Item label
            content: Item content (will be encrypted if is_sensitive=True)
            item_type: Item type (TEXT, URL, CODE, PATH)
            icon: Item icon (optional)
            is_sensitive: Whether content is sensitive (will encrypt content)
            is_favorite: Whether item is marked as favorite
            tags: List of tags (optional)
            description: Item description (optional)
            working_dir: Working directory for CODE items (optional)
            color: Item color for visual identification (optional)
            is_active: Whether item is active (default True)
            is_archived: Whether item is archived (default False)
            is_list: Whether item is part of a list (default False)
            list_group: Name/identifier of the list group (optional)
            orden_lista: Position of item within the list (default 0)

        Returns:
            int: New item ID
        """
        # Encrypt content if sensitive
        if is_sensitive and content:
            from core.encryption_manager import EncryptionManager
            encryption_manager = EncryptionManager()
            content = encryption_manager.encrypt(content)
            logger.info(f"Content encrypted for sensitive item: {label}")

        tags_json = json.dumps(tags or [])
        query = """
            INSERT INTO items
            (category_id, label, content, type, icon, is_sensitive, is_favorite, tags, description, working_dir, color, is_active, is_archived, is_list, list_group, orden_lista, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        item_id = self.execute_update(
            query,
            (category_id, label, content, item_type, icon, is_sensitive, is_favorite, tags_json, description, working_dir, color, is_active, is_archived, is_list, list_group, orden_lista)
        )
        list_info = f", List: {list_group}[{orden_lista}]" if is_list else ""
        logger.info(f"Item added: {label} (ID: {item_id}, Sensitive: {is_sensitive}, Favorite: {is_favorite}, Active: {is_active}, Archived: {is_archived}{list_info})")
        return item_id

    def update_item(self, item_id: int, **kwargs) -> None:
        """
        Update item fields

        Args:
            item_id: Item ID to update
            **kwargs: Fields to update (label, content, type, icon, is_sensitive, is_favorite, tags, description, working_dir, is_active, is_archived, is_list, list_group, orden_lista)
        """
        allowed_fields = ['label', 'content', 'type', 'icon', 'is_sensitive', 'is_favorite', 'tags', 'description', 'working_dir', 'color', 'is_active', 'is_archived', 'is_list', 'list_group', 'orden_lista']
        updates = []
        params = []

        # Get current item to check if it's sensitive
        current_item = self.get_item(item_id)
        if not current_item:
            logger.warning(f"Item not found for update: ID {item_id}")
            return

        # Check if item is being marked as sensitive or if it's already sensitive
        is_currently_sensitive = current_item.get('is_sensitive', False)
        will_be_sensitive = kwargs.get('is_sensitive', is_currently_sensitive)

        for field, value in kwargs.items():
            if field in allowed_fields:
                # Handle tags serialization
                if field == 'tags':
                    value = json.dumps(value)
                # Handle content encryption for sensitive items
                elif field == 'content' and will_be_sensitive and value:
                    from core.encryption_manager import EncryptionManager
                    encryption_manager = EncryptionManager()
                    # Only encrypt if not already encrypted
                    if not encryption_manager.is_encrypted(value):
                        value = encryption_manager.encrypt(value)
                        logger.info(f"Content encrypted for item ID: {item_id}")

                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(item_id)
            query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Item updated: ID {item_id}")

    def delete_item(self, item_id: int) -> None:
        """
        Delete item

        Args:
            item_id: Item ID to delete
        """
        query = "DELETE FROM items WHERE id = ?"
        self.execute_update(query, (item_id,))
        logger.info(f"Item deleted: ID {item_id}")

    def update_last_used(self, item_id: int) -> None:
        """
        Update item's last_used timestamp

        Args:
            item_id: Item ID
        """
        query = "UPDATE items SET last_used = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (item_id,))
        logger.debug(f"Last used updated: ID {item_id}")

    def get_all_items(self, include_inactive: bool = False) -> List[Dict]:
        """
        Get ALL items from ALL categories with category info

        Args:
            include_inactive: Include items from inactive categories

        Returns:
            List[Dict]: List of all items with category_name, category_icon, category_color
        """
        query = """
            SELECT
                i.*,
                c.name as category_name,
                c.icon as category_icon,
                c.color as category_color,
                c.id as category_id
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE c.is_active = 1 OR ? = 1
            ORDER BY i.created_at DESC
        """
        results = self.execute_query(query, (include_inactive,))

        # Initialize encryption manager for decrypting sensitive items
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        # Parse tags and decrypt sensitive content
        for item in results:
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        return results

    def search_items(self, search_query: str, limit: int = 50) -> List[Dict]:
        """
        Search items by label or content

        Args:
            search_query: Search text
            limit: Maximum results

        Returns:
            List[Dict]: List of matching items with category name
        """
        query = """
            SELECT i.*, c.name as category_name
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.label LIKE ? OR i.content LIKE ? OR i.tags LIKE ?
            ORDER BY i.last_used DESC
            LIMIT ?
        """
        search_pattern = f"%{search_query}%"
        results = self.execute_query(
            query,
            (search_pattern, search_pattern, search_pattern, limit)
        )

        # Parse tags
        for item in results:
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

        return results

    # ========== LISTAS AVANZADAS ==========

    def create_list(self, category_id: int, list_name: str, items_data: List[Dict[str, Any]]) -> List[int]:
        """
        Crea una lista completa con múltiples items

        Args:
            category_id: ID de la categoría
            list_name: Nombre de la lista (list_group)
            items_data: Lista de dicts con datos de cada paso
                [
                    {'label': 'Paso 1', 'content': '...', 'type': 'TEXT'},
                    {'label': 'Paso 2', 'content': '...', 'type': 'CODE'},
                ]

        Returns:
            List[int]: Lista de IDs de los items creados
        """
        if not items_data or len(items_data) < 1:
            raise ValueError("La lista debe tener al menos 1 item")

        # Validar que el nombre de lista sea único
        if not self.is_list_name_unique(category_id, list_name):
            raise ValueError(f"El nombre de lista '{list_name}' ya existe en esta categoría")

        item_ids = []

        try:
            with self.transaction() as conn:
                for orden, item_data in enumerate(items_data, start=1):
                    # Agregar item con campos de lista
                    item_id = self.add_item(
                        category_id=category_id,
                        label=item_data.get('label', f'Paso {orden}'),
                        content=item_data.get('content', ''),
                        item_type=item_data.get('type', 'TEXT'),
                        icon=item_data.get('icon'),
                        is_sensitive=item_data.get('is_sensitive', False),
                        tags=item_data.get('tags'),
                        description=item_data.get('description'),
                        working_dir=item_data.get('working_dir'),
                        color=item_data.get('color'),
                        # Campos de lista
                        is_list=True,
                        list_group=list_name,
                        orden_lista=orden
                    )
                    item_ids.append(item_id)

                logger.info(f"Lista creada: '{list_name}' con {len(item_ids)} items en categoría {category_id}")

            return item_ids

        except Exception as e:
            logger.error(f"Error al crear lista '{list_name}': {e}")
            raise

    def get_lists_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene resumen de todas las listas en una categoría

        Args:
            category_id: ID de la categoría

        Returns:
            List[Dict]: Lista de diccionarios con info de cada lista
                [
                    {
                        'list_group': 'Deploy Producción',
                        'item_count': 5,
                        'first_label': 'Pull cambios',
                        'created_at': '2025-10-31 10:00:00'
                    },
                    ...
                ]
        """
        query = """
            SELECT
                list_group,
                COUNT(*) as item_count,
                MIN(label) as first_label,
                MIN(created_at) as created_at,
                MAX(last_used) as last_used
            FROM items
            WHERE category_id = ?
            AND is_list = 1
            AND is_active = 1
            GROUP BY list_group
            ORDER BY created_at DESC
        """
        results = self.execute_query(query, (category_id,))
        logger.debug(f"Encontradas {len(results)} listas en categoría {category_id}")
        return results

    def get_list_items(self, category_id: int, list_group: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los items de una lista específica, ordenados por orden_lista

        Args:
            category_id: ID de la categoría
            list_group: Nombre de la lista

        Returns:
            List[Dict]: Lista de items ordenados (con contenido desencriptado si es sensible)
        """
        query = """
            SELECT * FROM items
            WHERE category_id = ?
            AND is_list = 1
            AND list_group = ?
            AND is_active = 1
            ORDER BY orden_lista ASC
        """
        results = self.execute_query(query, (category_id, list_group))

        # Desencriptar y parsear tags (mismo proceso que en get_items_by_category)
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        for item in results:
            # Parse tags
            if item['tags']:
                try:
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        logger.debug(f"Obtenidos {len(results)} items de lista '{list_group}'")
        return results

    def reorder_list_item(self, item_id: int, new_orden: int) -> bool:
        """
        Cambia el orden de un item dentro de su lista
        También reordena los demás items afectados

        Args:
            item_id: ID del item a reordenar
            new_orden: Nueva posición (1, 2, 3...)

        Returns:
            bool: True si se reordenó exitosamente
        """
        # Obtener info del item
        item = self.get_item(item_id)
        if not item or not item.get('is_list'):
            logger.warning(f"Item {item_id} no encontrado o no es parte de una lista")
            return False

        category_id = item['category_id']
        list_group = item['list_group']
        old_orden = item['orden_lista']

        if old_orden == new_orden:
            logger.debug(f"Item {item_id} ya está en la posición {new_orden}")
            return True

        try:
            with self.transaction() as conn:
                cursor = conn.cursor()

                # Si movemos hacia arriba (new_orden < old_orden)
                # Incrementar orden de los items entre new_orden y old_orden
                if new_orden < old_orden:
                    cursor.execute("""
                        UPDATE items
                        SET orden_lista = orden_lista + 1
                        WHERE category_id = ?
                        AND list_group = ?
                        AND orden_lista >= ?
                        AND orden_lista < ?
                    """, (category_id, list_group, new_orden, old_orden))

                # Si movemos hacia abajo (new_orden > old_orden)
                # Decrementar orden de los items entre old_orden y new_orden
                else:
                    cursor.execute("""
                        UPDATE items
                        SET orden_lista = orden_lista - 1
                        WHERE category_id = ?
                        AND list_group = ?
                        AND orden_lista > ?
                        AND orden_lista <= ?
                    """, (category_id, list_group, old_orden, new_orden))

                # Actualizar el item movido
                cursor.execute("""
                    UPDATE items
                    SET orden_lista = ?
                    WHERE id = ?
                """, (new_orden, item_id))

                logger.info(f"Item {item_id} reordenado de posición {old_orden} a {new_orden} en lista '{list_group}'")
                return True

        except Exception as e:
            logger.error(f"Error al reordenar item {item_id}: {e}")
            return False

    def delete_list(self, category_id: int, list_group: str) -> bool:
        """
        Elimina TODOS los items de una lista

        Args:
            category_id: ID de la categoría
            list_group: Nombre de la lista a eliminar

        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            query = """
                DELETE FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
            """
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (category_id, list_group))
                deleted_count = cursor.rowcount

                logger.info(f"Lista '{list_group}' eliminada ({deleted_count} items) de categoría {category_id}")
                return True

        except Exception as e:
            logger.error(f"Error al eliminar lista '{list_group}': {e}")
            return False

    def update_list(self, category_id: int, old_list_group: str,
                   new_list_group: str = None, items_data: List[Dict[str, Any]] = None) -> bool:
        """
        Actualiza una lista existente

        Permite:
        - Renombrar la lista (cambiar list_group)
        - Actualizar los items de la lista (agregar/eliminar/modificar pasos)

        Args:
            category_id: ID de la categoría
            old_list_group: Nombre actual de la lista
            new_list_group: Nuevo nombre (opcional, si se quiere renombrar)
            items_data: Nuevos datos de items (opcional, si se quiere actualizar contenido)

        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            with self.transaction() as conn:
                # Caso 1: Solo renombrar
                if new_list_group and new_list_group != old_list_group:
                    # Validar que el nuevo nombre sea único
                    if not self.is_list_name_unique(category_id, new_list_group, exclude_list=old_list_group):
                        raise ValueError(f"El nombre '{new_list_group}' ya existe en esta categoría")

                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE items
                        SET list_group = ?
                        WHERE category_id = ?
                        AND list_group = ?
                        AND is_list = 1
                    """, (new_list_group, category_id, old_list_group))

                    logger.info(f"Lista renombrada: '{old_list_group}' → '{new_list_group}'")

                # Caso 2: Actualizar items de la lista
                if items_data is not None:
                    # Eliminar items actuales
                    final_list_name = new_list_group if new_list_group else old_list_group
                    self.delete_list(category_id, final_list_name)

                    # Crear nuevos items
                    self.create_list(category_id, final_list_name, items_data)

                    logger.info(f"Lista '{final_list_name}' actualizada con {len(items_data)} items")

                return True

        except Exception as e:
            logger.error(f"Error al actualizar lista '{old_list_group}': {e}")
            return False

    def is_list_name_unique(self, category_id: int, list_name: str, exclude_list: str = None) -> bool:
        """
        Verifica si el nombre de lista es único en la categoría

        Args:
            category_id: ID de la categoría
            list_name: Nombre de lista a verificar
            exclude_list: Nombre de lista a excluir (útil para edición)

        Returns:
            bool: True si el nombre es único, False si ya existe
        """
        if exclude_list:
            query = """
                SELECT COUNT(*) as count
                FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
                AND list_group != ?
            """
            result = self.execute_query(query, (category_id, list_name, exclude_list))
        else:
            query = """
                SELECT COUNT(*) as count
                FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
            """
            result = self.execute_query(query, (category_id, list_name))

        count = result[0]['count'] if result else 0
        is_unique = count == 0

        logger.debug(f"Nombre de lista '{list_name}' en categoría {category_id}: {'único' if is_unique else 'ya existe'}")
        return is_unique

    # ========== CLIPBOARD HISTORY ==========

    def add_to_history(self, item_id: Optional[int], content: str) -> int:
        """
        Add entry to clipboard history

        Args:
            item_id: Associated item ID (optional)
            content: Copied content

        Returns:
            int: History entry ID
        """
        query = """
            INSERT INTO clipboard_history (item_id, content)
            VALUES (?, ?)
        """
        history_id = self.execute_update(query, (item_id, content))
        logger.debug(f"History entry added: ID {history_id}")

        # Auto-trim history to max_history setting
        max_history = self.get_setting('max_history', 20)
        self.trim_history(keep_latest=max_history)

        return history_id

    def get_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent clipboard history

        Args:
            limit: Maximum entries to retrieve

        Returns:
            List[Dict]: List of history entries
        """
        query = """
            SELECT h.*, i.label, i.type
            FROM clipboard_history h
            LEFT JOIN items i ON h.item_id = i.id
            ORDER BY h.copied_at DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    def clear_history(self) -> None:
        """Clear all clipboard history"""
        query = "DELETE FROM clipboard_history"
        self.execute_update(query)
        logger.info("Clipboard history cleared")

    def trim_history(self, keep_latest: int = 20) -> None:
        """
        Keep only the latest N history entries

        Args:
            keep_latest: Number of entries to keep
        """
        query = """
            DELETE FROM clipboard_history
            WHERE id NOT IN (
                SELECT id FROM clipboard_history
                ORDER BY copied_at DESC
                LIMIT ?
            )
        """
        self.execute_update(query, (keep_latest,))
        logger.debug(f"History trimmed to {keep_latest} entries")

    # ========== PINNED PANELS ==========

    def save_pinned_panel(self, category_id: int, x_pos: int, y_pos: int,
                         width: int, height: int, is_minimized: bool = False,
                         custom_name: str = None, custom_color: str = None,
                         filter_config: str = None, keyboard_shortcut: str = None) -> int:
        """
        Save a pinned panel configuration to database

        Args:
            category_id: Category ID for this panel
            x_pos: X position on screen
            y_pos: Y position on screen
            width: Panel width
            height: Panel height
            is_minimized: Whether panel is minimized
            custom_name: Custom name for panel (optional)
            custom_color: Custom header color (optional, hex format)
            filter_config: Filter configuration as JSON string (optional)
            keyboard_shortcut: Keyboard shortcut string like 'Ctrl+Shift+1' (optional)

        Returns:
            int: New panel ID
        """
        query = """
            INSERT INTO pinned_panels
            (category_id, x_position, y_position, width, height, is_minimized,
             custom_name, custom_color, filter_config, keyboard_shortcut, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """
        panel_id = self.execute_update(
            query,
            (category_id, x_pos, y_pos, width, height, is_minimized, custom_name, custom_color, filter_config, keyboard_shortcut)
        )
        logger.info(f"Pinned panel saved: Category {category_id} (ID: {panel_id}, Shortcut: {keyboard_shortcut})")
        return panel_id

    def get_pinned_panels(self, active_only: bool = True) -> List[Dict]:
        """
        Retrieve all pinned panels

        Args:
            active_only: Only return panels marked as active

        Returns:
            List[Dict]: List of panel dictionaries with category info
        """
        if active_only:
            query = """
                SELECT p.*, c.name as category_name, c.icon as category_icon
                FROM pinned_panels p
                JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
                ORDER BY p.last_opened DESC
            """
            panels = self.execute_query(query)
        else:
            query = """
                SELECT p.*, c.name as category_name, c.icon as category_icon
                FROM pinned_panels p
                JOIN categories c ON p.category_id = c.id
                ORDER BY p.last_opened DESC
            """
            panels = self.execute_query(query)
        logger.debug(f"Retrieved {len(panels)} pinned panels (active_only={active_only})")
        return panels

    def get_panel_by_id(self, panel_id: int) -> Optional[Dict]:
        """
        Get specific panel by ID

        Args:
            panel_id: Panel ID

        Returns:
            Optional[Dict]: Panel dictionary with category info, or None
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
        """
        result = self.execute_query(query, (panel_id,))
        return result[0] if result else None

    def update_pinned_panel(self, panel_id: int, **kwargs) -> bool:
        """
        Update panel configuration

        Args:
            panel_id: Panel ID to update
            **kwargs: Fields to update (x_position, y_position, width, height,
                     is_minimized, custom_name, custom_color, filter_config,
                     keyboard_shortcut, is_active)

        Returns:
            bool: True if update successful
        """
        allowed_fields = [
            'x_position', 'y_position', 'width', 'height', 'is_minimized',
            'custom_name', 'custom_color', 'filter_config', 'keyboard_shortcut', 'is_active'
        ]
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            params.append(panel_id)
            query = f"UPDATE pinned_panels SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Pinned panel updated: ID {panel_id}")
            return True
        return False

    def update_panel_last_opened(self, panel_id: int) -> None:
        """
        Update last_opened timestamp and increment open_count

        Args:
            panel_id: Panel ID
        """
        query = """
            UPDATE pinned_panels
            SET last_opened = CURRENT_TIMESTAMP,
                open_count = open_count + 1
            WHERE id = ?
        """
        self.execute_update(query, (panel_id,))
        logger.debug(f"Panel {panel_id} opened - statistics updated")

    def delete_pinned_panel(self, panel_id: int) -> bool:
        """
        Remove a pinned panel from database

        Args:
            panel_id: Panel ID to delete

        Returns:
            bool: True if deletion successful
        """
        query = "DELETE FROM pinned_panels WHERE id = ?"
        self.execute_update(query, (panel_id,))
        logger.info(f"Pinned panel deleted: ID {panel_id}")
        return True

    def get_recent_panels(self, limit: int = 10) -> List[Dict]:
        """
        Get recently opened panels ordered by last_opened DESC

        Args:
            limit: Maximum number of panels to return

        Returns:
            List[Dict]: List of panel dictionaries with category info
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            JOIN categories c ON p.category_id = c.id
            ORDER BY p.last_opened DESC
            LIMIT ?
        """
        panels = self.execute_query(query, (limit,))
        logger.debug(f"Retrieved {len(panels)} recent panels")
        return panels

    def deactivate_all_panels(self) -> None:
        """
        Set is_active=0 for all panels (called on app shutdown)
        """
        query = "UPDATE pinned_panels SET is_active = 0"
        self.execute_update(query)
        logger.info("All pinned panels marked as inactive")

    def get_panel_by_category(self, category_id: int) -> Optional[Dict]:
        """
        Check if an active panel for this category already exists

        Args:
            category_id: Category ID

        Returns:
            Optional[Dict]: Panel dictionary if exists, None otherwise
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            JOIN categories c ON p.category_id = c.id
            WHERE p.category_id = ? AND p.is_active = 1
            LIMIT 1
        """
        result = self.execute_query(query, (category_id,))
        return result[0] if result else None

    # ========== BROWSER CONFIG ==========

    def get_browser_config(self) -> Dict:
        """
        Get browser configuration from database.

        Returns:
            Dict: Browser configuration or default values if not exists
        """
        query = "SELECT * FROM browser_config LIMIT 1"
        try:
            result = self.execute_query(query)
            if result:
                config = result[0]
                logger.debug(f"Browser config loaded: {config}")
                return config
            else:
                # No config exists, insert default
                logger.info("No browser config found, creating default")
                default_config = {
                    'home_url': 'https://www.google.com',
                    'is_visible': False,
                    'width': 500,
                    'height': 700
                }
                self.save_browser_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading browser config: {e}")
            # Return default config on error
            return {
                'home_url': 'https://www.google.com',
                'is_visible': False,
                'width': 500,
                'height': 700
            }

    def save_browser_config(self, config: Dict) -> bool:
        """
        Save browser configuration to database.

        Args:
            config: Dictionary with browser settings
                   (home_url, is_visible, width, height)

        Returns:
            bool: True if save successful
        """
        try:
            # Check if config exists
            query = "SELECT id FROM browser_config LIMIT 1"
            result = self.execute_query(query)

            if result:
                # Update existing config
                config_id = result[0]['id']
                update_query = """
                    UPDATE browser_config
                    SET home_url = ?,
                        is_visible = ?,
                        width = ?,
                        height = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                self.execute_update(
                    update_query,
                    (
                        config.get('home_url', 'https://www.google.com'),
                        config.get('is_visible', False),
                        config.get('width', 500),
                        config.get('height', 700),
                        config_id
                    )
                )
                logger.info(f"Browser config updated: ID {config_id}")
            else:
                # Insert new config
                insert_query = """
                    INSERT INTO browser_config (home_url, is_visible, width, height)
                    VALUES (?, ?, ?, ?)
                """
                self.execute_update(
                    insert_query,
                    (
                        config.get('home_url', 'https://www.google.com'),
                        config.get('is_visible', False),
                        config.get('width', 500),
                        config.get('height', 700)
                    )
                )
                logger.info("Browser config created")

            return True

        except Exception as e:
            logger.error(f"Error saving browser config: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
