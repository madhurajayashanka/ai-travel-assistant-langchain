import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from models import get_db_connection

class CacheManager:
    """Manage caching for API responses to reduce API costs."""
    
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = Path(__file__).parent.parent / "data" / "db.sqlite"
    
    def _generate_key(self, query_data, api_type):
        """Generate a unique key for a query."""
        if isinstance(query_data, dict):
            query_string = json.dumps(query_data, sort_keys=True)
        else:
            query_string = str(query_data)
        
        # Include API type in the hash to separate caches
        query_string = f"{api_type}:{query_string}"
        return hashlib.md5(query_string.encode()).hexdigest()
    
    def get_cached_response(self, query_data, api_type):
        """Get a cached response if it exists and is not expired."""
        query_hash = self._generate_key(query_data, api_type)
        
        # Create a new connection for this operation
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_data, expires_at FROM api_cache WHERE query_hash = ? AND expires_at > ?",
                (query_hash, datetime.now().isoformat())
            )
            result = cursor.fetchone()
            
            if result:
                return json.loads(result['response_data'])
                
            # Check file cache as fallback
            cache_file = self.cache_dir / f"{query_hash}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    if cache_data.get('expires_at', '') > datetime.now().isoformat():
                        return cache_data.get('response')
                except:
                    pass
                    
            return None
        finally:
            # Always close the connection
            conn.close()
    
    def cache_response(self, query_data, response_data, api_type, expire_hours=24):
        """Cache an API response."""
        query_hash = self._generate_key(query_data, api_type)
        expires_at = (datetime.now() + timedelta(hours=expire_hours)).isoformat()
        
        # Create a new connection for this operation
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO api_cache (query_hash, response_data, api_type, expires_at) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(query_hash) DO UPDATE SET
                        response_data = excluded.response_data,
                        expires_at = excluded.expires_at
                    """,
                    (query_hash, json.dumps(response_data), api_type, expires_at)
                )
                conn.commit()
            except sqlite3.Error as e:
                print(f"Database error: {e}")
                # Fallback to file cache if database fails
                self._save_to_file_cache(query_hash, response_data, expires_at)
        finally:
            # Always close the connection
            conn.close()
    
    def _save_to_file_cache(self, query_hash, response_data, expires_at):
        """Save cache data to file as a fallback mechanism."""
        cache_file = self.cache_dir / f"{query_hash}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'response': response_data,
                    'expires_at': expires_at
                }, f)
        except Exception as e:
            print(f"Error writing to file cache: {e}")
    
    def clear_expired_cache(self):
        """Clear expired cache entries."""
        now = datetime.now().isoformat()
        
        # Create a new connection for this operation
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM api_cache WHERE expires_at < ?", (now,))
            conn.commit()
        finally:
            conn.close()
        
        # Also clear any file-based cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                if cache_data.get('expires_at', '') < now:
                    cache_file.unlink()
            except (json.JSONDecodeError, FileNotFoundError):
                # Remove corrupted cache files
                try:
                    cache_file.unlink()
                except:
                    pass