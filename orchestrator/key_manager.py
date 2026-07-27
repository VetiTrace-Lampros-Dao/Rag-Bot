import os
import sys
import threading
from dotenv import load_dotenv

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class KeyManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KeyManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.lock = threading.Lock()
        primary_key = os.getenv("GEMINI_API_KEY")
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        
        self.keys = []
        if keys_str:
            # Parse comma-separated keys
            self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            
        # Add primary key to the list if not already present
        if primary_key and primary_key not in self.keys:
            self.keys.insert(0, primary_key)
            
        # Deduplicate keys while preserving order
        seen = set()
        self.keys = [k for k in self.keys if not (k in seen or seen.add(k))]
        
        self.current_index = 0
        
        # Sync environment variables with the active key
        if self.keys:
            os.environ["GEMINI_API_KEY"] = self.keys[0]
            os.environ["GOOGLE_API_KEY"] = self.keys[0]

    def get_api_key(self) -> str:
        with self.lock:
            if not self.keys:
                raise ValueError("No Gemini API keys found in .env!")
            return self.keys[self.current_index]

    def rotate_key(self, failed_key: str = None) -> str:
        with self.lock:
            if not self.keys:
                raise ValueError("No Gemini API keys found to rotate!")
            
            # If we've already rotated away from the failed key in another thread, do not rotate again
            if failed_key and failed_key != self.keys[self.current_index]:
                return self.keys[self.current_index]
                
            self.current_index = (self.current_index + 1) % len(self.keys)
            new_key = self.keys[self.current_index]
            print(f"\n[KEY_MANAGER] Rotating active API key to index {self.current_index} (starts with {new_key[:15]}...)", file=sys.stderr)
            
            # Update env vars for any standard clients reading from env
            os.environ["GEMINI_API_KEY"] = new_key
            os.environ["GOOGLE_API_KEY"] = new_key
            return new_key

    def execute_with_rotation(self, func, max_retries=None):
        """Execute a function passing the active API key. If a rate limit/429 error occurs, rotate key and retry."""
        if max_retries is None:
            max_retries = len(self.keys) if self.keys else 1

        last_exception = None
        for attempt in range(max_retries):
            current_key = self.get_api_key()
            try:
                return func(current_key)
            except Exception as e:
                err_str = str(e).lower()
                if any(term in err_str for term in ["429", "quota", "resourceexhausted", "rate limit", "exceeded", "limit"]):
                    print(f"[KEY_MANAGER] API Key rate-limited (attempt {attempt+1}/{max_retries}): {err_str[:120]}... Rotating key.", file=sys.stderr)
                    self.rotate_key(failed_key=current_key)
                    last_exception = e
                else:
                    raise e
        if last_exception:
            raise last_exception

    async def aexecute_with_rotation(self, async_func, max_retries=None):
        """Async version of execute_with_rotation."""
        if max_retries is None:
            max_retries = len(self.keys) if self.keys else 1

        last_exception = None
        for attempt in range(max_retries):
            current_key = self.get_api_key()
            try:
                return await async_func(current_key)
            except Exception as e:
                err_str = str(e).lower()
                if any(term in err_str for term in ["429", "quota", "resourceexhausted", "rate limit", "exceeded", "limit"]):
                    print(f"[KEY_MANAGER] Async API Key rate-limited (attempt {attempt+1}/{max_retries}): {err_str[:120]}... Rotating key.", file=sys.stderr)
                    self.rotate_key(failed_key=current_key)
                    last_exception = e
                else:
                    raise e
        if last_exception:
            raise last_exception

key_manager = KeyManager()

