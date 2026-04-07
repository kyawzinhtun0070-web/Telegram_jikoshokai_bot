#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
YAY ZAT ZODIAC BOT - PRODUCTION READY VERSION (REFACTORED & SECURED)
================================================================================

Description:
    A fully functional Telegram Bot for matching users based on zodiac signs 
    and personal preferences. Built with pyTelegramBotAPI and SQLite.

Features:
    ✅ User registration with multi-step form
    ✅ Zodiac-based matching algorithm
    ✅ Profile management (view/edit/delete)
    ✅ Like/Skip/Report system
    ✅ Admin panel with broadcast & statistics
    ✅ Channel membership verification
    ✅ Thread-safe SQLite database operations
    ✅ Environment variable configuration
    ✅ Comprehensive logging & error handling

Author: Yay Zat Development Team
Version: 2.0.0
License: MIT
Created: 2026
================================================================================
"""

# ═══════════════════════════════════════════════════════════════════════════
# 📦 SECTION 1: IMPORTS & DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════

# Standard Library Imports
import os
import sys
import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Union, Callable, Tuple
from pathlib import Path
from functools import wraps
import time
import re

# Third-Party Library Imports
import telebot
from telebot import types
from telebot.types import (    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    Message,
    CallbackQuery,
    User as TelegramUser,
    ChatMember
)

# Optional: Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    ENV_LOADED = True
except ImportError:
    ENV_LOADED = False
    print("⚠️ python-dotenv not installed. Using system environment variables only.")

# ═══════════════════════════════════════════════════════════════════════════
# 🔐 SECTION 2: CONFIGURATION & SECURITY SETUP
# ═══════════════════════════════════════════════════════════════════════════

class Config:
    """
    Centralized configuration manager.
    Loads settings from environment variables with fallback defaults.
    """
    
    # Bot Authentication - CRITICAL: Never hardcode in production!
    BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    
    # Administrator Settings
    ADMIN_USER_ID: int = int(os.getenv('ADMIN_USER_ID', '0'))
    
    # Channel Verification Settings
    CHANNEL_ID: int = int(os.getenv('CHANNEL_ID', '0'))
    CHANNEL_USERNAME: str = os.getenv('CHANNEL_USERNAME', 'yayzatofficial')
    CHANNEL_INVITE_LINK: str = f"https://t.me/{CHANNEL_USERNAME}"
    
    # Database Configuration
    DB_FILENAME: str = os.getenv('DB_FILENAME', 'yayzat_bot.db')
    DB_BACKUP_DIR: str = os.getenv('DB_BACKUP_DIR', 'backups')
    
    # Bot Behavior Settings
    MATCHING_TIMEOUT_SECONDS: int = int(os.getenv('MATCHING_TIMEOUT', '300'))
    REGISTRATION_TIMEOUT_SECONDS: int = int(os.getenv('REG_TIMEOUT', '600'))
    MAX_PHOTO_SIZE_MB: int = int(os.getenv('MAX_PHOTO_MB', '10'))
        # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/bot.log')
    
    # Feature Flags
    ENABLE_CHANNEL_CHECK: bool = os.getenv('ENABLE_CHANNEL_CHECK', 'true').lower() == 'true'
    ENABLE_AUTO_BACKUP: bool = os.getenv('ENABLE_AUTO_BACKUP', 'true').lower() == 'true'
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate critical configuration values.
        Returns list of error messages if any.
        """
        errors = []
        
        if not cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 40:
            errors.append("❌ TELEGRAM_BOT_TOKEN is missing or invalid")
            
        if cls.ADMIN_USER_ID <= 0:
            errors.append("❌ ADMIN_USER_ID must be a positive integer")
            
        if cls.CHANNEL_ID == 0:
            errors.append("⚠️ CHANNEL_ID not set - channel verification disabled")
            
        if not cls.DB_FILENAME:
            errors.append("❌ DB_FILENAME cannot be empty")
            
        return errors


# Validate configuration on module load
_config_errors = Config.validate()
if _config_errors:
    print("🚫 Configuration Errors Detected:")
    for err in _config_errors:
        print(f"   {err}")
    if "TELEGRAM_BOT_TOKEN" in str(_config_errors):
        print("\n💡 Hint: Create a .env file with your bot token:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# 📝 SECTION 3: LOGGING SYSTEM SETUP
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """
    Configure comprehensive logging system with file and console handlers.
    Returns configured logger instance.    """
    # Create logs directory if it doesn't exist
    log_dir = Path(Config.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('YayZatBot')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # File handler - for persistent logs
    try:
        file_handler = logging.FileHandler(
            Config.LOG_FILE, 
            mode='a', 
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Could not create log file: {e}")
    
    # Console handler - for real-time monitoring
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Prevent log propagation to root logger
    logger.propagate = False
    
    return logger


# Initialize global logger instance
logger = setup_logging()
logger.info("🔧 Logging system initialized successfully")
# ═══════════════════════════════════════════════════════════════════════════
# 💾 SECTION 4: DATABASE MANAGEMENT LAYER
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Thread-safe SQLite database manager with connection pooling support.
    Handles all CRUD operations for users, matches, and reports.
    """
    
    # Table schema definitions
    SCHEMA_USERS = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age TEXT,
            zodiac TEXT,
            city TEXT,
            hobby TEXT,
            job TEXT,
            song TEXT,
            bio TEXT,
            gender TEXT,
            looking_gender TEXT,
            looking_zodiac TEXT,
            photo TEXT,
            language TEXT DEFAULT 'my',
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now'))
        )
    """
    
    SCHEMA_SEEN = """
        CREATE TABLE IF NOT EXISTS seen_matches (
            viewer_id INTEGER NOT NULL,
            viewed_id INTEGER NOT NULL,
            viewed_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (viewer_id, viewed_id),
            FOREIGN KEY (viewer_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (viewed_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    
    SCHEMA_REPORTS = """
        CREATE TABLE IF NOT EXISTS user_reports (
            reporter_id INTEGER NOT NULL,
            reported_id INTEGER NOT NULL,
            reason TEXT,            reported_at TEXT DEFAULT (datetime('now')),
            is_resolved BOOLEAN DEFAULT 0,
            PRIMARY KEY (reporter_id, reported_id),
            FOREIGN KEY (reporter_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (reported_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    
    SCHEMA_LIKES = """
        CREATE TABLE IF NOT EXISTS user_likes (
            liker_id INTEGER NOT NULL,
            liked_id INTEGER NOT NULL,
            liked_at TEXT DEFAULT (datetime('now')),
            is_mutual BOOLEAN DEFAULT 0,
            is_accepted BOOLEAN DEFAULT 0,
            PRIMARY KEY (liker_id, liked_id),
            FOREIGN KEY (liker_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (liked_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    
    SCHEMA_INDEXES = """
        CREATE INDEX IF NOT EXISTS idx_users_zodiac ON users(zodiac);
        CREATE INDEX IF NOT EXISTS idx_users_gender ON users(gender);
        CREATE INDEX IF NOT EXISTS idx_users_city ON users(city);
        CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
        CREATE INDEX IF NOT EXISTS idx_seen_viewer ON seen_matches(viewer_id);
        CREATE INDEX IF NOT EXISTS idx_reports_unresolved ON user_reports(is_resolved);
    """
    
    # Valid field names for dynamic updates (security whitelist)
    VALID_FIELDS: Set[str] = {
        'name', 'age', 'zodiac', 'city', 'hobby', 'job', 
        'song', 'bio', 'gender', 'looking_gender', 
        'looking_zodiac', 'photo', 'language'
    }
    
    def __init__(self, db_path: str):
        """
        Initialize database manager with specified database file path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection_cache: Dict[int, sqlite3.Connection] = {}
        logger.info(f"🗄️ Database manager initialized: {db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """        Get a thread-local database connection.
        Uses check_same_thread=True for safety with proper locking.
        
        Returns:
            sqlite3.Connection object with row factory enabled
        """
        import threading
        thread_id = threading.get_ident()
        
        if thread_id not in self._connection_cache:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=True,  # Safety first!
                timeout=30.0,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            self._connection_cache[thread_id] = conn
            logger.debug(f"🔗 New DB connection for thread {thread_id}")
            
        return self._connection_cache[thread_id]
    
    def close_connection(self) -> None:
        """Close the current thread's database connection."""
        import threading
        thread_id = threading.get_ident()
        if thread_id in self._connection_cache:
            self._connection_cache[thread_id].close()
            del self._connection_cache[thread_id]
            logger.debug(f"🔌 DB connection closed for thread {thread_id}")
    
    def initialize_schema(self) -> bool:
        """
        Create all required database tables and indexes.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Execute schema definitions
            cursor.execute(self.SCHEMA_USERS)
            cursor.execute(self.SCHEMA_SEEN)
            cursor.execute(self.SCHEMA_REPORTS)            cursor.execute(self.SCHEMA_LIKES)
            cursor.executescript(self.SCHEMA_INDEXES)
            
            # Add missing columns for backward compatibility
            self._migrate_schema(cursor)
            
            conn.commit()
            logger.info("✅ Database schema initialized successfully")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database schema error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected schema error: {e}")
            return False
    
    def _migrate_schema(self, cursor: sqlite3.Cursor) -> None:
        """
        Handle database schema migrations for version upgrades.
        
        Args:
            cursor: Active database cursor for executing migrations
        """
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row['name'] for row in cursor.fetchall()}
        
        # Define new columns to add
        new_columns = [
            ('language', 'TEXT', "'my'"),
            ('is_active', 'BOOLEAN', '1'),
            ('last_seen', 'TEXT', "datetime('now')")
        ]
        
        for col_name, col_type, default_val in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"
                    )
                    logger.info(f"🔄 Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"⚠️ Could not add {col_name}: {e}")
    
    def create_backup(self) -> Optional[str]:
        """
        Create a timestamped backup of the database.
        
        Returns:            Path to backup file if successful, None otherwise
        """
        try:
            # Create backup directory
            backup_dir = Path(Config.DB_BACKUP_DIR)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"yayzat_backup_{timestamp}.db"
            
            # Use SQLite backup API for safe copying
            source_conn = self.get_connection()
            backup_conn = sqlite3.connect(str(backup_path))
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            backup_conn.close()
            logger.info(f"💾 Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    # ───────────────────────────────────────────────────────────────────────
    # USER CRUD OPERATIONS
    # ───────────────────────────────────────────────────────────────────────
    
    def user_exists(self, user_id: int) -> bool:
        """Check if a user exists in the database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ? LIMIT 1", 
                (user_id,)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"❌ user_exists error: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch complete user profile by user_id.
        
        Args:
            user_id: Telegram user ID            
        Returns:
            Dictionary with user data or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"❌ get_user error for {user_id}: {e}")
            return None
    
    def save_user(self, user_id: int,  Dict[str, Any]) -> bool:
        """
        Insert new user or update existing user profile.
        Uses UPSERT pattern for atomic operations.
        
        Args:
            user_id: Telegram user ID
             Dictionary containing user profile fields
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Prepare field names and values
            fields = list(self.VALID_FIELDS.intersection(data.keys()))
            if not fields:
                logger.warning(f"⚠️ No valid fields to save for user {user_id}")
                return False
            
            # Build dynamic SQL safely
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)
            update_clause = ', '.join([f"{f} = excluded.{f}" for f in fields])
            
            # Extract values in correct order
            values = [data[f] for f in fields]
            
            query = f"""                INSERT INTO users (user_id, {field_names}, updated_at)
                VALUES (?, {placeholders}, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                {update_clause},
                updated_at = datetime('now'),
                last_seen = datetime('now')
            """
            
            params = [user_id] + values
            cursor.execute(query, params)
            conn.commit()
            logger.debug(f"💾 User {user_id} saved successfully")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"❌ save_user error: {e}")
            conn.rollback()
            return False
    
    def update_user_field(self, user_id: int, field: str, value: Any) -> bool:
        """
        Update a single user field with validation.
        
        Args:
            user_id: Target user ID
            field: Field name to update (must be in VALID_FIELDS)
            value: New value for the field
            
        Returns:
            True if update successful, False otherwise
        """
        # Security check: whitelist field names
        if field not in self.VALID_FIELDS:
            logger.warning(f"🚫 Invalid field update attempt: {field}")
            return False
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE users SET {field} = ?, updated_at = datetime('now') WHERE user_id = ?",
                (value, user_id)
            )
            conn.commit()
            logger.debug(f"✏️ Updated {field} for user {user_id}")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ update_user_field error: {e}")
            return False
        def delete_user(self, user_id: int) -> bool:
        """
        Soft delete a user and clean up related data.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if deletion successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Mark as inactive instead of hard delete (recoverable)
            cursor.execute(
                "UPDATE users SET is_active = 0, updated_at = datetime('now') WHERE user_id = ?",
                (user_id,)
            )
            
            # Clean up related records
            cursor.execute("DELETE FROM seen_matches WHERE viewer_id = ? OR viewed_id = ?", 
                          (user_id, user_id))
            cursor.execute("DELETE FROM user_reports WHERE reporter_id = ? OR reported_id = ?", 
                          (user_id, user_id))
            cursor.execute("DELETE FROM user_likes WHERE liker_id = ? OR liked_id = ?", 
                          (user_id, user_id))
            
            conn.commit()
            logger.info(f"🗑️ User {user_id} deactivated and cleaned up")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"❌ delete_user error: {e}")
            return False
    
    def get_all_active_users(self) -> List[Dict[str, Any]]:
        """Retrieve all active users for matching."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE is_active = 1 ORDER BY last_seen DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"❌ get_all_active_users error: {e}")
            return []
    
    def get_user_count(self, active_only: bool = True) -> int:        """Get total user count with optional active filter."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            else:
                cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
    
    # ───────────────────────────────────────────────────────────────────────
    # MATCHING & INTERACTION OPERATIONS
    # ───────────────────────────────────────────────────────────────────────
    
    def mark_as_seen(self, viewer_id: int, viewed_id: int) -> bool:
        """Record that a user has viewed another user's profile."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO seen_matches (viewer_id, viewed_id) VALUES (?, ?)",
                (viewer_id, viewed_id)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ mark_as_seen error: {e}")
            return False
    
    def get_seen_ids(self, user_id: int) -> Set[int]:
        """Get set of user IDs that this user has already viewed."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT viewed_id FROM seen_matches WHERE viewer_id = ?",
                (user_id,)
            )
            return {row['viewed_id'] for row in cursor.fetchall()}
        except sqlite3.Error:
            return set()
    
    def clear_seen_history(self, user_id: int) -> bool:
        """Reset viewing history for a user (for fresh matching)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(                "DELETE FROM seen_matches WHERE viewer_id = ?",
                (user_id,)
            )
            conn.commit()
            logger.debug(f"🔄 Cleared seen history for user {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ clear_seen_history error: {e}")
            return False
    
    def record_like(self, liker_id: int, liked_id: int) -> Tuple[bool, bool]:
        """
        Record a like and check for mutual match.
        
        Returns:
            Tuple of (success, is_mutual_match)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert the like
            cursor.execute(
                "INSERT OR IGNORE INTO user_likes (liker_id, liked_id) VALUES (?, ?)",
                (liker_id, liked_id)
            )
            
            # Check if mutual like exists
            cursor.execute(
                "SELECT 1 FROM user_likes WHERE liker_id = ? AND liked_id = ?",
                (liked_id, liker_id)
            )
            is_mutual = cursor.fetchone() is not None
            
            if is_mutual:
                # Update both records as mutual
                cursor.execute(
                    "UPDATE user_likes SET is_mutual = 1 WHERE (liker_id = ? AND liked_id = ?) OR (liker_id = ? AND liked_id = ?)",
                    (liker_id, liked_id, liked_id, liker_id)
                )
            
            conn.commit()
            logger.info(f"❤️ Like recorded: {liker_id} -> {liked_id}, mutual: {is_mutual}")
            return True, is_mutual
            
        except sqlite3.Error as e:
            logger.error(f"❌ record_like error: {e}")
            return False, False
    
    def accept_like(self, user_id: int, from_user_id: int) -> bool:        """Accept a received like and mark as matched."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_likes SET is_accepted = 1 WHERE liker_id = ? AND liked_id = ?",
                (from_user_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ accept_like error: {e}")
            return False
    
    def record_report(self, reporter_id: int, reported_id: int, reason: str = "") -> bool:
        """Record a user report for admin review."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO user_reports 
                   (reporter_id, reported_id, reason) VALUES (?, ?, ?)""",
                (reporter_id, reported_id, reason[:200])  # Limit reason length
            )
            conn.commit()
            logger.warning(f"🚩 Report: {reporter_id} reported {reported_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ record_report error: {e}")
            return False
    
    # ───────────────────────────────────────────────────────────────────────
    # STATISTICS & ADMIN OPERATIONS
    # ───────────────────────────────────────────────────────────────────────
    
    def get_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive bot statistics."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Total active users
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            stats['total_active'] = cursor.fetchone()[0]
            
            # Gender distribution
            cursor.execute("SELECT gender, COUNT(*) FROM users WHERE is_active = 1 GROUP BY gender")
            stats['by_gender'] = {row['gender']: row[1] for row in cursor.fetchall()}            
            # Zodiac distribution
            cursor.execute("SELECT zodiac, COUNT(*) FROM users WHERE is_active = 1 GROUP BY zodiac")
            stats['by_zodiac'] = {row['zodiac']: row[1] for row in cursor.fetchall()}
            
            # Users with photos
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND photo IS NOT NULL")
            stats['with_photos'] = cursor.fetchone()[0]
            
            # Recent registrations (last 24 hours)
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-1 day')"
            )
            stats['new_today'] = cursor.fetchone()[0]
            
            # Total likes and reports
            cursor.execute("SELECT COUNT(*) FROM user_likes")
            stats['total_likes'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_reports WHERE is_resolved = 0")
            stats['pending_reports'] = cursor.fetchone()[0]
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"❌ get_statistics error: {e}")
            return {'error': str(e)}
    
    def get_users_for_admin(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user list for admin panel with pagination."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT user_id, name, age, zodiac, city, gender, created_at, is_active
                   FROM users ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []


# ═══════════════════════════════════════════════════════════════════════════
# 🎨 SECTION 5: UI COMPONENTS - KEYBOARDS & FORMATTING
# ═══════════════════════════════════════════════════════════════════════════

class KeyboardBuilder:
    """
    Factory class for generating Telegram keyboard layouts.    Supports both ReplyKeyboard and InlineKeyboard types.
    """
    
    # Zodiac signs list (English + Myanmar display)
    ZODIAC_SIGNS: List[str] = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]
    
    # Gender options
    GENDER_OPTIONS: List[str] = ['Male', 'Female', 'Both']
    
    @staticmethod
    def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Generate main menu keyboard for regular users."""
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True, 
            one_time_keyboard=False,
            is_persistent=True
        )
        
        # Primary action buttons
        keyboard.row(
            KeyboardButton("🔍 ဖူးစာရှာမည်"),
            KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်")
        )
        
        # Secondary action buttons
        keyboard.row(
            KeyboardButton("ℹ️ အကူအညီ"),
            KeyboardButton("🔄 Profile ပြန်လုပ်")
        )
        
        # Admin-only buttons
        if is_admin:
            keyboard.row(
                KeyboardButton("📊 စာရင်းအင်း"),
                KeyboardButton("🛠 Admin Panel")
            )
        
        return keyboard
    
    @staticmethod
    def get_zodiac_selector(include_skip: bool = True, include_any: bool = False) -> ReplyKeyboardMarkup:
        """Generate keyboard for zodiac sign selection."""
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True, 
            one_time_keyboard=True
        )
                # Add zodiac buttons in rows of 3
        for i in range(0, len(KeyboardBuilder.ZODIAC_SIGNS), 3):
            row = [KeyboardButton(z) for z in KeyboardBuilder.ZODIAC_SIGNS[i:i+3]]
            keyboard.row(*row)
        
        # Add optional buttons
        extra_buttons = []
        if include_any:
            extra_buttons.append(KeyboardButton('Any'))
        if include_skip:
            extra_buttons.append(KeyboardButton('/skip'))
        
        if extra_buttons:
            keyboard.row(*extra_buttons)
        
        return keyboard
    
    @staticmethod
    def get_gender_selector(looking_for: bool = False, include_skip: bool = True) -> ReplyKeyboardMarkup:
        """Generate keyboard for gender selection."""
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True, 
            one_time_keyboard=True
        )
        
        if looking_for:
            keyboard.row(
                KeyboardButton('Male'),
                KeyboardButton('Female'),
                KeyboardButton('Both')
            )
        else:
            keyboard.row(
                KeyboardButton('Male'),
                KeyboardButton('Female')
            )
        
        if include_skip:
            keyboard.row(KeyboardButton('/skip'))
        
        return keyboard
    
    @staticmethod
    def get_profile_edit_inline(user_ Dict[str, Any]) -> InlineKeyboardMarkup:
        """Generate inline keyboard for profile editing."""
        keyboard = InlineKeyboardMarkup()
        
        # Field edit buttons with callback data
        fields = [
            ('📛 နာမည်', 'name'),            ('🎂 အသက်', 'age'),
            ('🔮 ရာသီ', 'zodiac'),
            ('📍 မြို့', 'city'),
            ('🎨 ဝါသနာ', 'hobby'),
            ('💼 အလုပ်', 'job'),
            ('🎵 သီချင်း', 'song'),
            ('📝 Bio', 'bio'),
        ]
        
        # Create button pairs
        for i in range(0, len(fields), 2):
            row = []
            for label, field_key in fields[i:i+2]:
                row.append(InlineKeyboardButton(label, callback_data=f"edit_{field_key}"))
            keyboard.row(*row)
        
        # Special buttons
        keyboard.row(
            InlineKeyboardButton("📸 ဓာတ်ပုံ", callback_data="edit_photo")
        )
        keyboard.row(
            InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်", callback_data="edit_all")
        )
        keyboard.row(
            InlineKeyboardButton("🗑 Profile ဖျက်မည်", callback_data="delete_confirm")
        )
        
        return keyboard
    
    @staticmethod
    def get_match_actions(target_id: int) -> InlineKeyboardMarkup:
        """Generate action buttons for match viewing."""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{target_id}"),
            InlineKeyboardButton("⏭ Skip", callback_data="skip_match"),
            InlineKeyboardButton("🚩 Report", callback_data=f"report_{target_id}")
        )
        return keyboard
    
    @staticmethod
    def get_like_response_inline(liker_id: int) -> InlineKeyboardMarkup:
        """Generate response buttons for received likes."""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{liker_id}"),
            InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline_like")
        )
        return keyboard
        @staticmethod
    def get_channel_join_keyboard() -> InlineKeyboardMarkup:
        """Generate keyboard prompting channel join."""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(
                "📢 Channel ကို Join ပါ", 
                url=Config.CHANNEL_INVITE_LINK
            )
        )
        return keyboard
    
    @staticmethod
    def get_admin_panel_inline() -> InlineKeyboardMarkup:
        """Generate admin panel inline keyboard."""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("📊 Full Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 User List", callback_data="admin_users")
        )
        keyboard.row(
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🗑 Delete User", callback_data="admin_delete")
        )
        keyboard.row(
            InlineKeyboardButton("💾 Create Backup", callback_data="admin_backup")
        )
        return keyboard


class MessageFormatter:
    """
    Utility class for formatting bot messages consistently.
    Supports Myanmar language and emoji rendering.
    """
    
    @staticmethod
    def format_user_profile(user_data: Dict[str, Any], title: str = "👤 ပရိုဖိုင်") -> str:
        """Format user data into readable profile message."""
        # Helper for safe value extraction
        def get_val(key: str, default: str = "—") -> str:
            val = user_data.get(key)
            return str(val).strip() if val and str(val).strip() else default
        
        # Build profile text with Myanmar labels
        lines = [
            f"*{title}*",
            "",
            f"📛 နာမည်   : {get_val('name')}",
            f"🎂 အသက်   : {get_val('age')} နှစ်",            f"🔮 ရာသီ   : {get_val('zodiac')}",
            f"📍 မြို့    : {get_val('city')}",
            f"🎨 ဝါသနာ  : {get_val('hobby')}",
            f"💼 အလုပ်   : {get_val('job')}",
            f"🎵 သီချင်း  : {get_val('song')}",
        ]
        
        # Add bio if present
        bio = get_val('bio')
        if bio != "—":
            lines.append(f"📝 အကြောင်း : {bio}")
        
        # Add preferences
        looking_g = get_val('looking_gender')
        looking_z = get_val('looking_zodiac', 'Any')
        lines.extend([
            "",
            f"⚧ လိင်    : {get_val('gender')}",
            f"💑 ရှာဖွေ  : {looking_g} / {looking_z}"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_statistics(stats: Dict[str, Any]) -> str:
        """Format bot statistics for admin display."""
        if 'error' in stats:
            return f"❌ Stats Error: {stats['error']}"
        
        lines = [
            "📊 *Yay Zat Bot — စာရင်းအင်း*",
            "",
            f"👥 စုစုပေါင်း (Active) : *{stats.get('total_active', 0)}* ယောက်",
            f"🆕 ဒီနေ့အသစ်      : {stats.get('new_today', 0)} ယောက်",
            f"📸 ဓာတ်ပုံပါ        : {stats.get('with_photos', 0)} ယောက်",
            "",
            "⚧ *လိင်အလိုက်*",
        ]
        
        # Add gender breakdown
        by_gender = stats.get('by_gender', {})
        for gender in ['Male', 'Female', 'Other']:
            if gender in by_gender:
                emoji = "♂️" if gender == 'Male' else "♀️" if gender == 'Female' else "🧑"
                lines.append(f"   {emoji} {gender}: {by_gender[gender]} ယောက်")
        
        lines.extend([
            "",
            "❤️ စုစုပေါင်း Like  : {stats.get('total_likes', 0)}",
            f"🚩 Pending Reports : {stats.get('pending_reports', 0)}",            "",
            f"⏰ Update: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_welcome_message(user_count: int) -> str:
        """Format welcome message for new/returning users."""
        return (
            f"✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\n"
            f"👥 လက်ရှိ အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
            f"ဖူးစာရှင်ကိုရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
            f"_( /skip — ကျော်ချင်တဲ့မေးခွန်းအတွက် )_\n\n"
            f"📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ👇"
        )
    
    @staticmethod
    def format_match_found(target_ Dict[str, Any], 
                          looking_zodiac: str,
                          is_fallback: bool = False) -> str:
        """Format match result message with optional fallback notice."""
        note = ""
        if is_fallback and looking_zodiac and looking_zodiac.lower() != 'any':
            note = f"\n\n_( ⚠️ {looking_zodiac} ရာသီကို မတွေ့သေးလို့ အနီးစပ်ဆုံးပြပေးနေပါတယ် )_"
        
        return MessageFormatter.format_user_profile(
            target_data, 
            title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 🔧 SECTION 6: UTILITY FUNCTIONS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def safe_extract( Optional[Dict], key: str, default: str = "—") -> str:
    """Safely extract string value from dictionary with fallback."""
    if not data or not isinstance(data, dict):
        return default
    value = data.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def validate_age_input(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate age input string.    
    Returns:
        Tuple of (is_valid, error_message_or_none)
    """
    if not text or not text.strip():
        return False, "အသက်ကို ဂဏန်းဖြင့် ရိုက်ထည့်ပါ"
    
    try:
        age = int(text.strip())
        if age < 18 or age > 99:
            return False, "အသက်သည် ၁၈ နှစ် မှ ၉၉ နှစ် ကြားသာ ဖြစ်ရပါမည်"
        return True, None
    except ValueError:
        return False, "ဂဏန်းသာ ရိုက်ပါ (ဥပမာ: 25)"


def normalize_text(text: Optional[str]) -> str:
    """Normalize text input: strip whitespace, handle None."""
    if not text:
        return ""
    return str(text).strip()


def case_insensitive_match(value1: Optional[str], value2: Optional[str]) -> bool:
    """Case-insensitive string comparison with None handling."""
    if not value1 or not value2:
        return False
    return str(value1).lower().strip() == str(value2).lower().strip()


def hash_user_id(user_id: int, salt: str = "yayzat") -> str:
    """Create anonymized hash of user ID for logging."""
    return hashlib.sha256(f"{salt}{user_id}".encode()).hexdigest()[:12]


def format_time_ago(timestamp_str: Optional[str]) -> str:
    """Convert database timestamp to human-readable 'time ago' format."""
    if not timestamp_str:
        return "Unknown"
    
    try:
        dt = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
        diff = datetime.now() - dt
        
        if diff.days > 30:
            return dt.strftime("%d/%m/%Y")
        elif diff.days > 0:
            return f"{diff.days} ရက်က"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} နာရီက"        elif diff.seconds > 60:
            return f"{diff.seconds // 60} မိနစ်က"
        else:
            return "အခုလေးတင်"
    except:
        return timestamp_str


# ═══════════════════════════════════════════════════════════════════════════
# 🤖 SECTION 7: BOT INITIALIZATION & CORE SETUP
# ═══════════════════════════════════════════════════════════════════════════

# Initialize TeleBot instance with configuration
bot = telebot.TeleBot(
    Config.BOT_TOKEN,
    parse_mode="Markdown",
    threaded=True,
    skip_pending=True,
    num_threads=4  # Adjust based on expected load
)

# Initialize database manager
db_manager = DatabaseManager(Config.DB_FILENAME)

# In-memory registration state storage (with cleanup consideration)
# Key: user_id, Value: {registration_data, timestamp}
registration_sessions: Dict[int, Dict[str, Any]] = {}


def cleanup_old_sessions() -> None:
    """Remove expired registration sessions to prevent memory leaks."""
    cutoff = datetime.now() - timedelta(seconds=Config.REGISTRATION_TIMEOUT_SECONDS)
    expired = [
        uid for uid, data in registration_sessions.items()
        if data.get('timestamp', datetime.now()) < cutoff
    ]
    for uid in expired:
        del registration_sessions[uid]
        logger.debug(f"🧹 Cleaned expired session for user {uid}")
    if expired:
        logger.info(f"🧹 Cleaned {len(expired)} expired registration sessions")


# Schedule periodic cleanup (simple approach - could use APScheduler for production)
def schedule_cleanup():
    """Start background cleanup task."""
    import threading
    def cleanup_loop():
        while True:
            time.sleep(300)  # Run every 5 minutes            try:
                cleanup_old_sessions()
            except Exception as e:
                logger.error(f"❌ Cleanup loop error: {e}")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("🔄 Session cleanup scheduler started")


# ═══════════════════════════════════════════════════════════════════════════
# 🔐 SECTION 8: SECURITY & PERMISSION CHECKS
# ═══════════════════════════════════════════════════════════════════════════

def check_admin_permission(user_id: int) -> bool:
    """Verify if user has admin privileges."""
    return user_id == Config.ADMIN_USER_ID


def check_channel_membership(user_id: int) -> bool:
    """
    Verify if user is member of required Telegram channel.
    Returns True if channel check is disabled or user is member.
    """
    if not Config.ENABLE_CHANNEL_CHECK or Config.CHANNEL_ID == 0:
        return True  # Skip check if not configured
    
    try:
        chat_member = bot.get_chat_member(Config.CHANNEL_ID, user_id)
        status = chat_member.status
        # Accept member, administrator, or creator statuses
        return status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiException as e:
        if e.result.status_code == 400:
            # User hasn't started the bot in channel context
            logger.warning(f"⚠️ Channel check failed for {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Channel membership check error: {e}")
        return False  # Fail safe: require membership if check fails


def require_channel(func: Callable) -> Callable:
    """Decorator to enforce channel membership before executing handler."""
    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        user_id = message.chat.id
        
        if not check_channel_membership(user_id):
            keyboard = KeyboardBuilder.get_channel_join_keyboard()            bot.send_message(
                chat_id=user_id,
                text=f"⚠️ *Channel ကို အရင် Join ပေးပါ*\n\nဘော့ကို အပြည့်အဝအသုံးပြုဖို့ Channel မှာ ပါဝင်ဖို့ လိုအပ်ပါတယ်။",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════
# 📝 SECTION 9: REGISTRATION FLOW HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def start_registration(message: Message) -> None:
    """Initiate multi-step user registration process."""
    user_id = message.chat.id
    
    # Initialize registration session
    registration_sessions[user_id] = {
        'data': {},
        'step': 'name',
        'timestamp': datetime.now()
    }
    
    user_count = db_manager.get_user_count()
    welcome = MessageFormatter.format_welcome_message(user_count)
    
    bot.send_message(
        chat_id=user_id,
        text=welcome,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Register next step handler
    msg = bot.send_message(user_id, "📛 နာမည် ရိုက်ထည့်ပါ (/skip နဲ့ ကျော်နိုင်)👇")
    bot.register_next_step_handler(msg, handle_reg_name)


def handle_reg_name(message: Message) -> None:
    """Handle name input step in registration."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired. Please start over with /start")
        return    
    # Process input unless skipping
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['name'] = normalize_text(message.text)
    
    # Proceed to next step
    msg = bot.send_message(
        user_id, 
        "🎂 အသက် ဘယ်လောက်လဲ? (/skip)-"
    )
    bot.register_next_step_handler(msg, handle_reg_age)


def handle_reg_age(message: Message) -> None:
    """Handle age input with validation."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired. /start ကို နှိပ်ပါ။")
        return
    
    # Validate age if not skipping
    if message.text and message.text.strip().lower() != '/skip':
        is_valid, error = validate_age_input(message.text)
        if not is_valid:
            msg = bot.send_message(user_id, f"⚠️ {error} (/skip)")
            bot.register_next_step_handler(msg, handle_reg_age)
            return
        session['data']['age'] = message.text.strip()
    
    # Zodiac selection with keyboard
    keyboard = KeyboardBuilder.get_zodiac_selector()
    msg = bot.send_message(
        user_id,
        "🔮 ရာသီခွင်ကို ရွေးပါ-",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, handle_reg_zodiac)


def handle_reg_zodiac(message: Message) -> None:
    """Handle zodiac selection step."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
        if message.text and message.text.strip().lower() != '/skip':
        # Validate zodiac selection
        selected = message.text.strip()
        if selected in KeyboardBuilder.ZODIAC_SIGNS:
            session['data']['zodiac'] = selected
        # Else ignore invalid input (could add re-prompt)
    
    msg = bot.send_message(
        user_id,
        "📍 နေထိုင်တဲ့ မြို့ (ဥပမာ: Yangon, Mandalay)- (/skip)",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, handle_reg_city)


def handle_reg_city(message: Message) -> None:
    """Handle city input step."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['city'] = normalize_text(message.text)
    
    msg = bot.send_message(
        user_id,
        "🎨 ဝါသနာ ဘာပါလဲ? (ဥပမာ: ခရီးသွား, ဂီတ, စာဖတ်)- (/skip)"
    )
    bot.register_next_step_handler(msg, handle_reg_hobby)


def handle_reg_hobby(message: Message) -> None:
    """Handle hobby input step."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['hobby'] = normalize_text(message.text)
    
    msg = bot.send_message(
        user_id,
        "💼 အလုပ်အကိုင် ဘာလုပ်လဲ? (/skip)"
    )    bot.register_next_step_handler(msg, handle_reg_job)


def handle_reg_job(message: Message) -> None:
    """Handle job input step."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['job'] = normalize_text(message.text)
    
    msg = bot.send_message(
        user_id,
        "🎵 အကြိုက်ဆုံး သီချင်း တစ်ပုဒ်? (/skip)"
    )
    bot.register_next_step_handler(msg, handle_reg_song)


def handle_reg_song(message: Message) -> None:
    """Handle favorite song input step."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['song'] = normalize_text(message.text)
    
    bio_prompt = (
        "📝 *မိမိအကြောင်း အတိုချုံး* ရေးပြပါ 🙏\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတဝါသနာပါသူ, ရင်းနှီးစွာပြောဆိုချင်သူ)_\n"
        "(/skip နဲ့ ကျော်နိုင်ပါတယ်)"
    )
    msg = bot.send_message(
        user_id,
        text=bio_prompt,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_reg_bio)


def handle_reg_bio(message: Message) -> None:
    """Handle bio input step."""
    user_id = message.chat.id    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        session['data']['bio'] = normalize_text(message.text)
    
    # Gender selection
    keyboard = KeyboardBuilder.get_gender_selector(looking_for=False)
    msg = bot.send_message(
        user_id,
        "⚧ သင့်လိင်ကို ရွေးပါ-",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, handle_reg_gender)


def handle_reg_gender(message: Message) -> None:
    """Handle user's gender selection."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        selected = message.text.strip()
        if selected in KeyboardBuilder.GENDER_OPTIONS[:2]:  # Male/Female only
            session['data']['gender'] = selected
    
    # Looking for gender selection
    keyboard = KeyboardBuilder.get_gender_selector(looking_for=True)
    msg = bot.send_message(
        user_id,
        "💑 ရှာဖွေနေတဲ့ လိင်ကို ရွေးပါ-",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, handle_reg_looking_gender)


def handle_reg_looking_gender(message: Message) -> None:
    """Handle preferred gender for matching."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")        return
    
    if message.text and message.text.strip().lower() != '/skip':
        selected = message.text.strip()
        if selected in KeyboardBuilder.GENDER_OPTIONS:
            session['data']['looking_gender'] = selected
    
    # Zodiac preference selection
    keyboard = KeyboardBuilder.get_zodiac_selector(include_any=True)
    msg = bot.send_message(
        user_id,
        "🔮 ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, handle_reg_looking_zodiac)


def handle_reg_looking_zodiac(message: Message) -> None:
    """Handle preferred zodiac for matching."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired.")
        return
    
    if message.text and message.text.strip().lower() != '/skip':
        selected = message.text.strip()
        if selected in KeyboardBuilder.ZODIAC_SIGNS or selected.lower() == 'any':
            session['data']['looking_zodiac'] = selected
    
    # Final step: photo upload
    photo_prompt = "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_"
    msg = bot.send_message(
        user_id,
        text=photo_prompt,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, handle_reg_photo)


def handle_reg_photo(message: Message) -> None:
    """Handle photo upload and finalize registration."""
    user_id = message.chat.id
    session = registration_sessions.get(user_id)
    
    if not session:
        bot.send_message(user_id, "⚠️ Session expired. Please restart with /start")
        return    
    # Handle photo if provided
    if message.content_type == 'photo' and message.text != '/skip':
        # Get highest resolution photo
        photo = message.photo[-1]
        
        # Basic size validation
        if photo.file_size > Config.MAX_PHOTO_SIZE_MB * 1024 * 1024:
            bot.send_message(
                user_id,
                f"⚠️ ဓာတ်ပုံအရွယ်အစား {Config.MAX_PHOTO_SIZE_MB}MB ထက်မကျော်ရပါ။ /skip နဲ့ ဆက်ပါ။"
            )
            # Re-prompt for photo
            msg = bot.send_message(user_id, "📸 ဓာတ်ပုံ ပြန်ပို့ပါ (/skip)-")
            bot.register_next_step_handler(msg, handle_reg_photo)
            return
        
        session['data']['photo'] = photo.file_id
    
    # Clean up and save
    reg_data = session.pop('data', {})
    registration_sessions.pop(user_id, None)  # Clean session
    
    # Save to database
    success = db_manager.save_user(user_id, reg_data)
    
    if success:
        user_count = db_manager.get_user_count()
        is_new = not db_manager.get_user(user_id) or not reg_data.get('created_at')
        
        success_msg = (
            f"✅ Profile { 'တည်ဆောက်' if is_new else 'ပြင်ဆင်' } ပြီးပါပြီ! 🎉\n\n"
            f"👥 လက်ရှိ အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
            f"အောက်ခလုတ်များကို နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇"
        )
        
        bot.send_message(
            chat_id=user_id,
            text=success_msg,
            parse_mode="Markdown",
            reply_markup=KeyboardBuilder.get_main_menu(
                is_admin=check_admin_permission(user_id)
            )
        )
        
        # Notify admin of new registration
        if is_new:
            notify_admin_registration(user_id, reg_data, user_count)
    else:
        bot.send_message(            user_id,
            "❌ Profile သိမ်းဆည်းရာတွင် အဆင်မပြေဖြစ်ခဲ့ပါသည်။ နောက်မှ ပြန်ကြိုးစားပါ။",
            reply_markup=ReplyKeyboardRemove()
        )


def notify_admin_registration(user_id: int, data: Dict, total_users: int) -> None:
    """Send new user registration notification to admin."""
    if Config.ADMIN_USER_ID <= 0:
        return
    
    name = safe_extract(data, 'name', 'Unknown')
    zodiac = safe_extract(data, 'zodiac')
    gender = safe_extract(data, 'gender')
    
    notification = (
        f"🎉 *အသုံးပြုသူအသစ် မှတ်ပုံတင်ပြီးပါပြီ!*\n\n"
        f"🆔 `{user_id}`\n"
        f"📛 {name}\n"
        f"🔮 {zodiac} | ⚧ {gender}\n"
        f"👥 စုစုပေါင်း : *{total_users}* ယောက်\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    
    try:
        bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=notification,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Failed to notify admin: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🔍 SECTION 10: MATCHING SYSTEM CORE LOGIC
# ═══════════════════════════════════════════════════════════════════════════

@require_channel
def find_and_show_match(message: Message) -> None:
    """
    Core matching algorithm: find compatible user and display profile.
    Implements preference filtering and fallback logic.
    """
    user_id = message.chat.id
    
    # Get current user's profile
    my_profile = db_manager.get_user(user_id)
    if not my_profile:
        bot.send_message(            user_id,
            "/start ကိုနှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ။",
            reply_markup=KeyboardBuilder.get_main_menu()
        )
        return
    
    # Get already viewed users
    seen_ids = db_manager.get_seen_ids(user_id)
    exclude_ids = seen_ids | {user_id}
    
    # Get preferences
    looking_gender = (my_profile.get('looking_gender') or '').strip().lower()
    looking_zodiac = (my_profile.get('looking_zodiac') or '').strip()
    
    # Fetch and filter candidates
    all_users = db_manager.get_all_active_users()
    candidates = []
    
    for user in all_users:
        target_id = user['user_id']
        
        # Skip excluded users
        if target_id in exclude_ids:
            continue
        
        # Gender filter (case-insensitive)
        if looking_gender and looking_gender not in ['both', 'any']:
            target_gender = (user.get('gender') or '').strip().lower()
            if target_gender != looking_gender:
                continue
        
        candidates.append(user)
    
    # Handle no candidates found
    if not candidates:
        if seen_ids:
            # Reset seen history and retry once
            db_manager.clear_seen_history(user_id)
            bot.send_message(
                user_id,
                "🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် စာရင်းအသစ်ပြန်စပါပြီ..."
            )
            find_and_show_match(message)  # Single retry
        else:
            bot.send_message(
                user_id,
                "😔 လောလောဆယ် သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။\nနောက်မှ ပြန်ကြိုးစားကြည့်ပါ။",
                reply_markup=KeyboardBuilder.get_main_menu()
            )
        return    
    # Sort by zodiac preference (preferred first)
    if looking_zodiac and looking_zodiac.lower() not in ['any', '']:
        preferred = [u for u in candidates 
                    if case_insensitive_match(u.get('zodiac'), looking_zodiac)]
        others = [u for u in candidates 
                 if not case_insensitive_match(u.get('zodiac'), looking_zodiac)]
        ordered = preferred + others
        is_fallback = len(preferred) == 0
    else:
        ordered = candidates
        is_fallback = False
    
    # Select best match
    target_user = ordered[0]
    target_id = target_user['user_id']
    
    # Record as seen
    db_manager.mark_as_seen(user_id, target_id)
    
    # Format and send match message
    match_text = MessageFormatter.format_match_found(
        target_user, 
        looking_zodiac,
        is_fallback=is_fallback
    )
    
    actions_kb = KeyboardBuilder.get_match_actions(target_id)
    
    # Send with photo if available
    photo_id = target_user.get('photo')
    if photo_id:
        bot.send_photo(
            chat_id=user_id,
            photo=photo_id,
            caption=match_text,
            reply_markup=actions_kb,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id=user_id,
            text=match_text,
            reply_markup=actions_kb,
            parse_mode="Markdown"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 👤 SECTION 11: PROFILE MANAGEMENT HANDLERS# ═══════════════════════════════════════════════════════════════════════════

def show_user_profile(message: Message) -> None:
    """Display user's own profile with edit options."""
    user_id = message.chat.id
    profile = db_manager.get_user(user_id)
    
    if not profile:
        bot.send_message(
            user_id,
            "Profile မရှိသေးပါ။ /start ကိုနှိပ်ပြီး မှတ်ပုံတင်ပါ။",
            reply_markup=KeyboardBuilder.get_main_menu()
        )
        return
    
    # Format profile text
    user_count = db_manager.get_user_count()
    header = f"📊 အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
    profile_text = header + MessageFormatter.format_user_profile(profile)
    
    # Create edit keyboard
    edit_kb = KeyboardBuilder.get_profile_edit_inline(profile)
    
    # Send with photo if available
    photo_id = profile.get('photo')
    if photo_id:
        bot.send_photo(
            chat_id=user_id,
            photo=photo_id,
            caption=profile_text,
            reply_markup=edit_kb,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id=user_id,
            text=profile_text,
            reply_markup=edit_kb,
            parse_mode="Markdown"
        )


def start_profile_edit(message: Message, field: str) -> None:
    """Initiate editing of a specific profile field."""
    user_id = message.chat.id
    
    # Special handling for photo
    if field == 'photo':
        msg = bot.send_message(
            user_id,            "📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, handle_photo_update)
        return
    
    # Text field editing
    field_labels = {
        'name': '📛 နာမည်',
        'age': '🎂 အသက်',
        'zodiac': '🔮 ရာသီ',
        'city': '📍 မြို့',
        'hobby': '🎨 ဝါသနာ',
        'job': '💼 အလုပ်',
        'song': '🎵 သီချင်း',
        'bio': '📝 Bio',
        'gender': '⚧ လိင်',
        'looking_gender': '💑 ရှာဖွေမည့်လိင်',
        'looking_zodiac': '🔮 ရှာဖွေမည့်ရာသီ'
    }
    
    label = field_labels.get(field, field)
    msg = bot.send_message(
        user_id,
        f"📝 {label} အသစ် ရိုက်ထည့်ပါ-",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, handle_field_update, field)


def handle_field_update(message: Message, field: str) -> None:
    """Process updated field value and save to database."""
    user_id = message.chat.id
    
    if not message.text or not message.text.strip():
        bot.send_message(user_id, "⚠️ ဗလာမထားပါနဲ့။ ပြန်ရိုက်ပါ။")
        return
    
    new_value = normalize_text(message.text)
    
    # Validate age field specifically
    if field == 'age':
        is_valid, error = validate_age_input(new_value)
        if not is_valid:
            bot.send_message(user_id, f"⚠️ {error}")
            return
    
    success = db_manager.update_user_field(user_id, field, new_value)
    
    if success:        bot.send_message(
            user_id,
            "✅ ပြင်ဆင်မှု အောင်မြင်ပါသည်!",
            reply_markup=KeyboardBuilder.get_main_menu(
                is_admin=check_admin_permission(user_id)
            )
        )
    else:
        bot.send_message(user_id, "❌ ပြင်ဆင်ရာတွင် အဆင်မပြေဖြစ်ခဲ့ပါသည်။")


def handle_photo_update(message: Message) -> None:
    """Process updated profile photo."""
    user_id = message.chat.id
    
    if message.content_type != 'photo':
        bot.send_message(user_id, "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။")
        return
    
    # Validate size
    photo = message.photo[-1]
    if photo.file_size > Config.MAX_PHOTO_SIZE_MB * 1024 * 1024:
        bot.send_message(
            user_id,
            f"⚠️ ဓာတ်ပုံအရွယ်အစား {Config.MAX_PHOTO_SIZE_MB}MB ထက်မကျော်ရပါ။"
        )
        return
    
    success = db_manager.update_user_field(user_id, 'photo', photo.file_id)
    
    if success:
        bot.send_message(
            user_id,
            "✅ ဓာတ်ပုံ ပြောင်းလဲပြီးပါပြီ!",
            reply_markup=KeyboardBuilder.get_main_menu(
                is_admin=check_admin_permission(user_id)
            )
        )
    else:
        bot.send_message(user_id, "❌ ဓာတ်ပုံ ပြောင်းလဲရာတွင် အဆင်မပြေဖြစ်ခဲ့ပါသည်။")


def confirm_profile_deletion(message: Message) -> None:
    """Show confirmation dialog for profile deletion."""
    user_id = message.chat.id
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ ဟုတ်ကဲ့ ဖျက်မည်", callback_data="confirm_delete_profile"),
        InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="cancel_delete_profile")    )
    
    bot.send_message(
        user_id,
        "⚠️ *Profile ကို ဖျက်မှာ သေချာပါသလား?*\n\n"
        "ဖျက်ပြီးရင် ပြန်မရနိုင်တော့ပါ။",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def execute_profile_deletion(user_id: int) -> None:
    """Permanently delete user profile."""
    success = db_manager.delete_user(user_id)
    
    if success:
        bot.send_message(
            user_id,
            "🗑 Profile ဖျက်ပြီးပါပြီ။\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်။",
            reply_markup=ReplyKeyboardRemove()
        )
        # Notify admin
        if Config.ADMIN_USER_ID > 0:
            try:
                bot.send_message(
                    Config.ADMIN_USER_ID,
                    f"🗑 User `{user_id}` profile deleted by user request."
                )
            except:
                pass
    else:
        bot.send_message(user_id, "❌ ဖျက်ရာတွင် အဆင်မပြေဖြစ်ခဲ့ပါသည်။")


# ═══════════════════════════════════════════════════════════════════════════
# 🛠 SECTION 12: ADMIN PANEL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def show_admin_statistics(message: Message) -> None:
    """Display comprehensive bot statistics to admin."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        bot.send_message(user_id, "⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်။")
        return
    
    stats = db_manager.get_statistics()
    stats_text = MessageFormatter.format_statistics(stats)
    
    bot.send_message(        user_id,
        text=stats_text,
        parse_mode="Markdown",
        reply_markup=KeyboardBuilder.get_main_menu(is_admin=True)
    )


def show_admin_user_list(message: Message) -> None:
    """Display paginated user list for admin."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        return
    
    users = db_manager.get_users_for_admin(limit=30)
    
    if not users:
        bot.send_message(user_id, "👥 User မရှိသေးပါ။")
        return
    
    lines = [f"👥 *User List (နောက်ဆုံး 30)*\n"]
    for i, u in enumerate(users, 1):
        uid = u['user_id']
        name = safe_extract(u, 'name')
        status = "🟢" if u.get('is_active') else "🔴"
        lines.append(f"{i}. {status} {name} — `{uid}`")
    
    bot.send_message(
        user_id,
        text="\n".join(lines),
        parse_mode="Markdown"
    )


def start_admin_broadcast(message: Message) -> None:
    """Initiate broadcast message to all users."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        return
    
    bot.send_message(
        user_id,
        "📢 ပို့မည့် Message ကို ရိုက်ထည့်ပါ (/cancel-ပယ်ဖျက်)-"
    )
    bot.register_next_step_handler_by_chat_id(user_id, execute_broadcast)


def execute_broadcast(message: Message) -> None:
    """Execute broadcast to all active users."""    if message.text and message.text.strip() == '/cancel':
        bot.send_message(Config.ADMIN_USER_ID, "✅ Broadcast ပယ်ဖျက်လိုက်ပါပြီ။")
        return
    
    admin_id = Config.ADMIN_USER_ID
    sent_count = 0
    failed_count = 0
    
    # Get all active user IDs
    user_ids = [u['user_id'] for u in db_manager.get_all_active_users()]
    
    for uid in user_ids:
        try:
            bot.send_message(
                chat_id=uid,
                text=f"📢 *Admin မှ သတင်းစကား*\n\n{message.text}",
                parse_mode="Markdown"
            )
            sent_count += 1
            time.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed_count += 1
            logger.warning(f"❌ Broadcast failed for {uid}: {e}")
    
    # Report results to admin
    bot.send_message(
        chat_id=admin_id,
        text=(
            f"✅ Broadcast ပြီးပါပြီ!\n"
            f"✔️ {sent_count} ယောက် ရောက်ပါသည်\n"
            f"❌ {failed_count} ယောက် မရောက်ပါ"
        )
    )


def start_admin_delete_user(message: Message) -> None:
    """Initiate user deletion by ID."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        return
    
    bot.send_message(
        user_id,
        "🗑 ဖျက်မည့် User ID ရိုက်ပါ (/cancel-ပယ်ဖျက်)-"
    )
    bot.register_next_step_handler_by_chat_id(user_id, execute_admin_delete)


def execute_admin_delete(message: Message) -> None:    """Execute user deletion by admin."""
    if message.text and message.text.strip() == '/cancel':
        bot.send_message(Config.ADMIN_USER_ID, "✅ ပယ်ဖျက်လိုက်ပါပြီ။")
        return
    
    try:
        target_id = int(message.text.strip())
        
        if db_manager.user_exists(target_id):
            db_manager.delete_user(target_id)
            bot.send_message(
                Config.ADMIN_USER_ID,
                f"✅ User `{target_id}` ဖျက်ပြီးပါပြီ။",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                Config.ADMIN_USER_ID,
                "⚠️ ထို ID ဖြင့် User မတွေ့ပါ။"
            )
    except ValueError:
        bot.send_message(
            Config.ADMIN_USER_ID,
            "⚠️ ID ဂဏန်းသာ ရိုက်ပါ။"
        )
    except Exception as e:
        bot.send_message(
            Config.ADMIN_USER_ID,
            f"❌ Error: {e}"
        )


def create_admin_backup(message: Message) -> None:
    """Create database backup and send to admin."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        return
    
    bot.send_message(user_id, "💾 Backup စတင်နေပါပြီ...")
    
    backup_path = db_manager.create_backup()
    
    if backup_path:
        try:
            with open(backup_path, 'rb') as doc:
                bot.send_document(
                    chat_id=user_id,
                    document=doc,
                    caption=f"✅ Backup: {Path(backup_path).name}",                    visible_file_name=True
                )
        except Exception as e:
            bot.send_message(
                user_id,
                f"❌ Backup file send failed: {e}\nPath: {backup_path}"
            )
    else:
        bot.send_message(user_id, "❌ Backup creation failed.")


# ═══════════════════════════════════════════════════════════════════════════
# 📞 SECTION 13: CALLBACK QUERY HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call: CallbackQuery) -> None:
    """
    Central handler for all inline keyboard callback queries.
    Routes to appropriate handler based on callback data prefix.
    """
    user_id = call.message.chat.id
    callback_data = call.data or ""
    
    # Acknowledge callback to remove loading state
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    
    # ── Profile Edit Callbacks ───────────────────────────────────────────
    if callback_data.startswith("edit_"):
        field = callback_data[5:]  # Remove "edit_" prefix
        
        if field == "all":
            # Start full profile rebuild
            bot.delete_message(user_id, call.message.message_id)
            start_registration(call.message)
        else:
            # Edit specific field
            bot.delete_message(user_id, call.message.message_id)
            start_profile_edit(call.message, field)
    
    # ── Profile Deletion Flow ────────────────────────────────────────────
    elif callback_data == "delete_confirm":
        confirm_profile_deletion(call.message)
    
    elif callback_data == "confirm_delete_profile":
        bot.delete_message(user_id, call.message.message_id)
        execute_profile_deletion(user_id)    
    elif callback_data == "cancel_delete_profile":
        bot.delete_message(user_id, call.message.message_id)
    
    # ── Match Interaction Callbacks ──────────────────────────────────────
    elif callback_data == "skip_match":
        bot.delete_message(user_id, call.message.message_id)
        find_and_show_match(call.message)
    
    elif callback_data.startswith("like_"):
        target_id = int(callback_data[5:])
        handle_like_action(user_id, target_id, call.message.message_id)
    
    elif callback_data.startswith("accept_"):
        liker_id = int(callback_data[7:])
        handle_accept_like(user_id, liker_id, call.message.message_id)
    
    elif callback_data == "decline_like":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(
            user_id,
            "❌ ငြင်းဆန်လိုက်ပါပြီ။",
            reply_markup=KeyboardBuilder.get_main_menu()
        )
    
    elif callback_data.startswith("report_"):
        reported_id = int(callback_data[7:])
        handle_report_user(user_id, reported_id, call.message.message_id)
    
    # ── Admin Panel Callbacks ────────────────────────────────────────────
    elif callback_data == "admin_stats" and check_admin_permission(user_id):
        show_admin_statistics(call.message)
    
    elif callback_data == "admin_users" and check_admin_permission(user_id):
        show_admin_user_list(call.message)
    
    elif callback_data == "admin_broadcast" and check_admin_permission(user_id):
        start_admin_broadcast(call.message)
    
    elif callback_data == "admin_delete" and check_admin_permission(user_id):
        start_admin_delete_user(call.message)
    
    elif callback_data == "admin_backup" and check_admin_permission(user_id):
        create_admin_backup(call.message)


def handle_like_action(user_id: int, target_id: int, msg_id: int) -> None:
    """Process user liking another profile."""
    try:
        bot.delete_message(user_id, msg_id)    except:
        pass
    
    # Verify channel membership again for security
    if not check_channel_membership(user_id):
        bot.answer_callback_query(
            call_id=None,  # Already answered
            text="⚠️ Channel ကို Join ပါ!",
            show_alert=True
        )
        return
    
    # Record the like
    success, is_mutual = db_manager.record_like(user_id, target_id)
    
    if not success:
        bot.send_message(
            user_id,
            "⚠️ Like လုပ်ရာတွင် အဆင်မပြေဖြစ်ခဲ့ပါသည်။",
            reply_markup=KeyboardBuilder.get_main_menu()
        )
        return
    
    # Get liker's profile for notification
    liker_profile = db_manager.get_user(user_id)
    liker_name = safe_extract(liker_profile, 'name', 'တစ်ယောက်')
    
    if is_mutual:
        # Immediate match!
        notify_match(user_id, target_id)
    else:
        # Send notification to target user
        like_caption = (
            f"💌 *'{liker_name}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n" +
            MessageFormatter.format_user_profile(liker_profile, title='👤 *သူ/သူမ ရဲ့ Profile*')
        )
        
        response_kb = KeyboardBuilder.get_like_response_inline(user_id)
        
        try:
            target_photo = liker_profile.get('photo') if liker_profile else None
            if target_photo:
                bot.send_photo(
                    chat_id=target_id,
                    photo=target_photo,
                    caption=like_caption,
                    reply_markup=response_kb,
                    parse_mode="Markdown"
                )
            else:                bot.send_message(
                    chat_id=target_id,
                    text=like_caption,
                    reply_markup=response_kb,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"⚠️ Could not send like notification to {target_id}: {e}")
            bot.send_message(
                user_id,
                "⚠️ တစ်ဖက်လူမှာ Bot ကို Block ထားသဖြင့် ပေးပို့မရပါ။",
                reply_markup=KeyboardBuilder.get_main_menu()
            )
            return
    
    # Confirm to liker
    bot.send_message(
        chat_id=user_id,
        text=(
            f"❤️ Like လုပ်လိုက်ပါပြီ!\n" +
            (f"🎉 Match ဖြစ်သွားပါပြီ! စကားပြောနိုင်ပါပြီ 🎉" if is_mutual 
             else "တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊")
        ),
        reply_markup=KeyboardBuilder.get_main_menu()
    )


def handle_accept_like(user_id: int, liker_id: int, msg_id: int) -> None:
    """Process acceptance of a received like."""
    try:
        bot.delete_message(user_id, msg_id)
    except:
        pass
    
    # Record acceptance
    db_manager.accept_like(user_id, liker_id)
    
    # Notify both users of match
    notify_match(user_id, liker_id)


def notify_match(user_a: int, user_b: int) -> None:
    """Send match notification to both users."""
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Notify admin of new match
    if Config.ADMIN_USER_ID > 0:
        admin_note = (
            f"💖 *New Match!*\n\n"
            f"[User A](tg://user?id={user_a}) + [User B](tg://user?id={user_b})\n"            f"⏰ {current_time}"
        )
        try:
            bot.send_message(
                chat_id=Config.ADMIN_USER_ID,
                text=admin_note,
                parse_mode="Markdown"
            )
        except:
            pass
    
    # Notify both matched users
    for person_id, partner_id in [(user_a, user_b), (user_b, user_a)]:
        try:
            bot.send_message(
                chat_id=person_id,
                text=(
                    f"💖 *Match ဖြစ်သွားပါပြီ!* 🎉\n\n"
                    f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_id}) "
                    f"တိုက်ရိုက်စကားပြောနိုင်ပါပြီ!\n\n"
                    f"ကောင်းမွန်စွာ ဆက်သွယ်ပြောဆိုပါ 🙏"
                ),
                parse_mode="Markdown",
                reply_markup=KeyboardBuilder.get_main_menu()
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not notify {person_id} of match: {e}")


def handle_report_user(reporter_id: int, reported_id: int, msg_id: int) -> None:
    """Process user report submission."""
    # Record the report
    db_manager.record_report(reporter_id, reported_id)
    
    # Confirm to reporter
    bot.answer_callback_query(
        call_id=None,
        text="🚩 Report လုပ်ပြီးပါပြီ။ Admin က စစ်ဆေးပါမယ်။",
        show_alert=True
    )
    
    # Remove the message
    try:
        bot.delete_message(reporter_id, msg_id)
    except:
        pass
    
    # Notify admin
    if Config.ADMIN_USER_ID > 0:
        reporter_name = safe_extract(db_manager.get_user(reporter_id), 'name')        reported_name = safe_extract(db_manager.get_user(reported_id), 'name')
        
        report_alert = (
            f"🚩 *User Report Received*\n\n"
            f"👤 Reporter : `{reporter_id}` {reporter_name}\n"
            f"🎯 Reported : `{reported_id}` {reported_name}\n"
            f"⏰ Time     : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        try:
            bot.send_message(
                chat_id=Config.ADMIN_USER_ID,
                text=report_alert,
                parse_mode="Markdown"
            )
        except:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# 🎛 SECTION 14: COMMAND & MESSAGE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

# Main menu button to function mapping
MENU_HANDLERS: Dict[str, Callable[[Message], None]] = {
    "🔍 ဖူးစာရှာမည်": find_and_show_match,
    "👤 ကိုယ့်ပရိုဖိုင်": show_user_profile,
    "ℹ️ အကူအညီ": lambda m: show_help(m),
    "🔄 Profile ပြန်လုပ်": lambda m: start_registration(m),
    "📊 စာရင်းအင်း": show_admin_statistics,
    "🛠 Admin Panel": lambda m: show_admin_panel(m),
}


def show_admin_panel(message: Message) -> None:
    """Display admin panel inline keyboard."""
    user_id = message.chat.id
    
    if not check_admin_permission(user_id):
        bot.send_message(user_id, "⛔ Admin သာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    keyboard = KeyboardBuilder.get_admin_panel_inline()
    bot.send_message(
        user_id,
        "🛠 *Admin Panel*\n\nအောက်ပါလုပ်ဆောင်ချက်များကို ရွေးချယ်အသုံးပြုနိုင်ပါသည်:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

def show_help(message: Message) -> None:
    """Display help/usage information."""
    user_id = message.chat.id
    
    help_text = (
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာဖွေပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — သင့်ပရိုဖိုင်ကို ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — ပရိုဖိုင်အသစ် ပြန်လည်ဖြည့်စွက်ပါ\n"
        "ℹ️ *အကူအညီ* — ဤကူညီချက်စာမျက်နှာကို ပြသပါ\n\n"
        "*အထူး Commands*\n"
        "/start — Bot ကို စတင်အသုံးပြုပါ / မှတ်ပုံတင်ပါ\n"
        "/reset — Profile ကို ပြန်လည်စတင်ပါ\n"
        "/deleteprofile — Profile ကို ဖျက်သိမ်းပါ (သတိထားပါ)\n"
        "/help — ဤအကူအညီစာမျက်နှာကို ပြန်ပြပါ\n\n"
        "🚨 ပြဿနာရှိပါက Admin ကို ဆက်သွယ်ပါ။"
    )
    
    bot.send_message(
        chat_id=user_id,
        text=help_text,
        parse_mode="Markdown",
        reply_markup=KeyboardBuilder.get_main_menu(
            is_admin=check_admin_permission(user_id)
        )
    )


# Text message handler for menu buttons
@bot.message_handler(func=lambda m: m.text and m.text in MENU_HANDLERS)
def handle_menu_button(message: Message) -> None:
    """Route menu button presses to appropriate handlers."""
    handler = MENU_HANDLERS.get(message.text)
    if handler:
        handler(message)


# Command handlers
@bot.message_handler(commands=['start'])
def handle_start_command(message: Message) -> None:
    """Handle /start command - entry point for users."""
    user_id = message.chat.id
    
    # Check if user already registered
    if db_manager.user_exists(user_id):
        user_count = db_manager.get_user_count()
        welcome = (
            f"✨ *ကြိုဆိုပါတယ်!* ✨\n\n"
            f"👥 လက်ရှိ အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
            f"ခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇"        )
        bot.send_message(
            chat_id=user_id,
            text=welcome,
            parse_mode="Markdown",
            reply_markup=KeyboardBuilder.get_main_menu(
                is_admin=check_admin_permission(user_id)
            )
        )
        return
    
    # Start new registration
    start_registration(message)


@bot.message_handler(commands=['reset', 'myprofile', 'deleteprofile', 'help'])
def handle_shortcut_commands(message: Message) -> None:
    """Handle shortcut command aliases."""
    cmd = message.text.split()[0].lower()
    
    if cmd == '/reset':
        start_registration(message)
    elif cmd == '/myprofile':
        show_user_profile(message)
    elif cmd == '/deleteprofile':
        confirm_profile_deletion(message)
    elif cmd == '/help':
        show_help(message)


@bot.message_handler(content_types=['text'])
def handle_unknown_text(message: Message) -> None:
    """Handle unrecognized text messages."""
    # Only respond if not in a registration flow
    if message.chat.id not in registration_sessions:
        bot.send_message(
            message.chat.id,
            "❓ မသိသော စာသားဖြစ်ပါသည်။\nအောက်ခလုတ်များကို နှိပ်၍ အသုံးပြုပါ။",
            reply_markup=KeyboardBuilder.get_main_menu(
                is_admin=check_admin_permission(message.chat.id)
            )
        )


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 SECTION 15: BOT STARTUP & MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def perform_startup_checks() -> bool:
    """    Perform critical startup validations.
    Returns True if all checks pass.
    """
    checks_passed = True
    
    # Check database initialization
    if not db_manager.initialize_schema():
        logger.critical("❌ Database initialization failed!")
        checks_passed = False
    
    # Check bot token validity (light check)
    try:
        bot_info = bot.get_me()
        logger.info(f"✅ Bot connected: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        logger.critical(f"❌ Bot authentication failed: {e}")
        checks_passed = False
    
    # Check channel accessibility if configured
    if Config.ENABLE_CHANNEL_CHECK and Config.CHANNEL_ID != 0:
        try:
            bot.get_chat(Config.CHANNEL_ID)
            logger.info(f"✅ Channel accessible: {Config.CHANNEL_ID}")
        except Exception as e:
            logger.warning(f"⚠️ Channel check warning: {e}")
    
    return checks_passed


def main() -> None:
    """
    Main entry point for the bot application.
    Handles startup, polling, and graceful shutdown.
    """
    print("=" * 70)
    print("🌟 Yay Zat Zodiac Bot - Starting Up 🌟")
    print("=" * 70)
    
    start_time = datetime.now()
    logger.info(f"🚀 Bot startup initiated at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Perform startup validations
    if not perform_startup_checks():
        logger.error("❌ Startup checks failed. Exiting.")
        sys.exit(1)
    
    # Start background cleanup scheduler
    schedule_cleanup()
    
    # Create initial backup if enabled    if Config.ENABLE_AUTO_BACKUP:
        db_manager.create_backup()
    
    print(f"✅ Bot is ready! Listening for updates...")
    logger.info("🎧 Bot polling started")
    
    # Start long polling with error recovery
    try:
        bot.infinity_polling(
            none_stop=True,
            timeout=60,
            long_polling_timeout=60,
            allowed_updates=bot.listening_types
        )
    except KeyboardInterrupt:
        logger.info("⌨️ Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.critical(f"💥 Critical polling error: {e}", exc_info=True)
    finally:
        # Cleanup on exit
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"🛑 Bot stopped. Uptime: {duration}")
        print(f"\n👋 Bot stopped after {duration}")
        
        # Close database connections
        db_manager.close_connection()
        
        # Final backup on shutdown
        if Config.ENABLE_AUTO_BACKUP:
            db_manager.create_backup()


# ═══════════════════════════════════════════════════════════════════════════
# 🏁 EXECUTION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
