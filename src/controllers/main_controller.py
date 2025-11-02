"""
Main Controller
"""
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_manager import ConfigManager
from core.clipboard_manager import ClipboardManager
from core.category_filter_engine import CategoryFilterEngine
from core.pinned_panels_manager import PinnedPanelsManager
from core.simple_browser_manager import SimpleBrowserManager
from controllers.clipboard_controller import ClipboardController
from controllers.list_controller import ListController
from models.category import Category
from models.item import Item
import logging

logger = logging.getLogger(__name__)


class MainController:
    """Main application controller - coordinates all app logic"""

    def __init__(self):
        # Initialize managers
        self.config_manager = ConfigManager(db_path="widget_sidebar.db")
        self.clipboard_manager = ClipboardManager()
        self.category_filter_engine = CategoryFilterEngine(db_path="widget_sidebar.db")
        self.pinned_panels_manager = PinnedPanelsManager(self.config_manager.db)
        self.browser_manager = SimpleBrowserManager(self.config_manager.db)

        # Initialize controllers
        self.clipboard_controller = ClipboardController(self.clipboard_manager)
        self.list_controller = ListController(self.config_manager.db, self.clipboard_manager)

        # Data
        self.categories: List[Category] = []  # All categories (unfiltered, for compatibility)
        self._all_categories: List[Category] = []  # Master list: ALL categories from DB
        self._filtered_categories: List[Category] = []  # Filtered categories for UI
        self._filters_active: bool = False  # Flag to track if filters are active
        self.current_category: Optional[Category] = None
        self.main_window = None  # Will be set by main.py

        # Load initial data
        self.load_data()

    def load_data(self) -> None:
        """Load configuration and categories"""
        print("Loading configuration...")
        self.config_manager.load_config()

        print("Loading categories...")
        self._all_categories = self.config_manager.load_default_categories()
        self.categories = self._all_categories  # Initially, categories = all categories
        self._filters_active = False

        print(f"Loaded {len(self.categories)} categories")
        for cat in self.categories:
            print(f"  - {cat.name}: {len(cat.items)} items")

    def get_categories(self, include_filtered: bool = True) -> List[Category]:
        """
        Get categories

        Args:
            include_filtered: If True and filters are active, return filtered categories.
                             If False, always return all categories from database.

        Returns:
            List of categories
        """
        if include_filtered and self._filters_active:
            # Return filtered categories if filters are active
            return self._filtered_categories
        else:
            # Return all categories (unfiltered)
            return self._all_categories

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a specific category by ID"""
        return self.config_manager.get_category(category_id)

    def set_current_category(self, category_id: str) -> bool:
        """Set the currently active category"""
        category = self.get_category(category_id)
        if category:
            self.current_category = category
            print(f"Active category: {category.name}")
            return True
        return False

    def get_current_category(self) -> Optional[Category]:
        """Get the currently active category"""
        return self.current_category

    def copy_item_to_clipboard(self, item: Item) -> bool:
        """Copy an item to clipboard"""
        return self.clipboard_controller.copy_item(item)

    def get_clipboard_history(self, limit: int = 10):
        """Get clipboard history"""
        return self.clipboard_controller.get_history(limit)

    def get_setting(self, key: str, default=None):
        """Get a configuration setting"""
        return self.config_manager.get_setting(key, default)

    def set_setting(self, key: str, value) -> bool:
        """Set a configuration setting"""
        return self.config_manager.set_setting(key, value)

    def apply_category_filters(self, filters: dict) -> None:
        """
        Apply category filters using CategoryFilterEngine

        Args:
            filters: Dictionary with filter criteria from CategoryFilterWindow
        """
        try:
            logger.info(f"Applying category filters: {filters}")

            # Use CategoryFilterEngine to get filtered categories
            filtered_categories = self.category_filter_engine.apply_filters(filters)

            logger.info(f"Filter result: {len(filtered_categories)} categories")

            # Store filtered categories separately (DO NOT replace self._all_categories)
            self._filtered_categories = filtered_categories
            self._filters_active = True

            # For backward compatibility, also update self.categories
            self.categories = filtered_categories

            # Update the UI (sidebar) if main_window is available
            if self.main_window:
                self.main_window.load_categories(filtered_categories)
                logger.debug("Sidebar updated with filtered categories")

            # Get and log filter stats
            stats = self.category_filter_engine.get_filter_stats()
            cache_stats = self.category_filter_engine.get_cache_stats()

            if stats:
                logger.info(
                    f"Filter stats: {stats.filtered_categories}/{stats.total_categories} "
                    f"categories, {stats.active_filters_count} filters, "
                    f"{stats.execution_time_ms:.2f}ms"
                )

            if cache_stats:
                logger.debug(
                    f"Cache stats: {cache_stats['cache_hits']} hits, "
                    f"{cache_stats['cache_misses']} misses, "
                    f"{cache_stats['hit_rate']:.1f}% hit rate, "
                    f"{cache_stats['cache_size']}/{cache_stats['cache_max_size']} entries"
                )

        except Exception as e:
            logger.error(f"Error applying category filters: {e}", exc_info=True)
            # On error, reload all categories
            self.load_all_categories()

    def load_all_categories(self) -> None:
        """
        Load all categories without filters (clear filters)
        """
        try:
            logger.info("Loading all categories (clearing filters)")

            # Clear filter engine cache (database may have changed)
            self.category_filter_engine.clear_cache()

            # Reload ALL categories from database
            self._all_categories = self.config_manager.load_default_categories()
            self.categories = self._all_categories  # Reset to all categories
            self._filtered_categories = []
            self._filters_active = False

            logger.info(f"Loaded {len(self.categories)} categories")

            # Update the UI (sidebar) if main_window is available
            if self.main_window:
                self.main_window.load_categories(self.categories)
                logger.debug("Sidebar updated with all categories")

        except Exception as e:
            logger.error(f"Error loading all categories: {e}", exc_info=True)

    def invalidate_filter_cache(self) -> None:
        """
        Invalidate filter engine cache when database changes
        This should be called after any category/item modifications
        """
        logger.debug("Invalidating filter engine cache")
        self.category_filter_engine.clear_cache()
        # Also clear config manager cache
        if hasattr(self.config_manager, '_categories_cache'):
            self.config_manager._categories_cache = None

    def toggle_browser(self):
        """Toggle browser window visibility"""
        try:
            logger.info("Toggling browser window")
            self.browser_manager.toggle_browser()
        except Exception as e:
            logger.error(f"Error toggling browser: {e}", exc_info=True)
            raise

    def __del__(self):
        """Cleanup: close database connection and browser"""
        if hasattr(self, 'browser_manager'):
            self.browser_manager.cleanup()
        if hasattr(self, 'config_manager'):
            self.config_manager.close()
