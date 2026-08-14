import os
import sys
import time
import asyncio
import threading
from dotenv import load_dotenv

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Default cooldown period (seconds) before a rate-limited key can be retried
DEFAULT_COOLDOWN = 60

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

        # Per-key cooldown tracking: key -> timestamp when cooldown expires
        self._cooldown_until: dict[str, float] = {}
        
        # Sync environment variables with the active key
        if self.keys:
            os.environ["GEMINI_API_KEY"] = self.keys[0]
            os.environ["GOOGLE_API_KEY"] = self.keys[0]

    def _is_key_cooled_down(self, key: str) -> bool:
        """Check if a key's cooldown has expired and it can be used again."""
        cooldown_expiry = self._cooldown_until.get(key, 0)
        if time.time() >= cooldown_expiry:
            # Cooldown expired — remove tracking entry
            self._cooldown_until.pop(key, None)
            return True
        return False

    def _mark_key_rate_limited(self, key: str, cooldown: float = DEFAULT_COOLDOWN):
        """Mark a key as rate-limited with a cooldown period."""
        self._cooldown_until[key] = time.time() + cooldown
        print(f"\n[KEY_MANAGER] Key {key[:15]}... rate-limited, cooldown {cooldown}s until {time.strftime('%H:%M:%S', time.localtime(self._cooldown_until[key]))}", file=sys.stderr)

    def get_api_key(self) -> str:
        with self.lock:
            if not self.keys:
                raise ValueError("No Gemini API keys found in .env!")
            return self.keys[self.current_index]

    def get_available_key(self) -> str | None:
        """Get the first available key that is not on cooldown. Returns None if all keys are on cooldown."""
        with self.lock:
            if not self.keys:
                raise ValueError("No Gemini API keys found in .env!")
            
            # Try each key starting from the one after current_index
            for i in range(len(self.keys)):
                idx = (self.current_index + i) % len(self.keys)
                key = self.keys[idx]
                if self._is_key_cooled_down(key):
                    if idx != self.current_index:
                        self.current_index = idx
                        os.environ["GEMINI_API_KEY"] = key
                        os.environ["GOOGLE_API_KEY"] = key
                        print(f"\n[KEY_MANAGER] Switched to available key index {idx} ({key[:15]}...)", file=sys.stderr)
                    return key
            
            # All keys on cooldown — find the one that expires soonest
            soonest_key = min(self._cooldown_until, key=lambda k: self._cooldown_until[k])
            wait_time = self._cooldown_until[soonest_key] - time.time()
            print(f"\n[KEY_MANAGER] All keys on cooldown. Soonest available in {wait_time:.1f}s", file=sys.stderr)
            return None

    def get_soonest_cooldown_remaining(self) -> float:
        """Return seconds until the next key becomes available. 0 if a key is already available."""
        with self.lock:
            if not self._cooldown_until:
                return 0
            # Check if any key is already available
            for key in self.keys:
                if self._is_key_cooled_down(key):
                    return 0
            soonest = min(self._cooldown_until.values())
            return max(0, soonest - time.time())

    def rotate_key(self, failed_key: str = None, cooldown: float = DEFAULT_COOLDOWN) -> str:
        with self.lock:
            if not self.keys:
                raise ValueError("No Gemini API keys found to rotate!")
            
            # If we've already rotated away from the failed key in another thread, do not rotate again
            if failed_key and failed_key != self.keys[self.current_index]:
                return self.keys[self.current_index]

            # Mark the failed key as rate-limited with cooldown
            if failed_key:
                self._mark_key_rate_limited(failed_key, cooldown)

            # Find the next key that is NOT on cooldown
            for i in range(1, len(self.keys) + 1):
                next_idx = (self.current_index + i) % len(self.keys)
                next_key = self.keys[next_idx]
                if self._is_key_cooled_down(next_key):
                    self.current_index = next_idx
                    print(f"\n[KEY_MANAGER] Rotating active API key to index {self.current_index} ({next_key[:15]}...)", file=sys.stderr)
                    os.environ["GEMINI_API_KEY"] = next_key
                    os.environ["GOOGLE_API_KEY"] = next_key
                    return next_key

            # All keys are on cooldown — advance to the next one anyway (round-robin)
            self.current_index = (self.current_index + 1) % len(self.keys)
            new_key = self.keys[self.current_index]
            print(f"\n[KEY_MANAGER] All keys on cooldown! Falling back to index {self.current_index} ({new_key[:15]}...)", file=sys.stderr)
            os.environ["GEMINI_API_KEY"] = new_key
            os.environ["GOOGLE_API_KEY"] = new_key
            return new_key

    def execute_with_rotation(self, func, max_retries=None):
        """Execute a function passing the active API key. If a rate limit/429 error occurs, rotate key and retry."""
        if max_retries is None:
            max_retries = len(self.keys) * 2 if self.keys else 1

        last_exception = None
        backoff = 1.0
        for attempt in range(max_retries):
            current_key = self.get_available_key()
            if current_key is None:
                # All keys on cooldown — wait for the soonest one
                wait = self.get_soonest_cooldown_remaining()
                print(f"[KEY_MANAGER] All keys cooling down, waiting {wait:.1f}s...", file=sys.stderr)
                time.sleep(wait + 0.5)
                current_key = self.get_api_key()

            try:
                return func(current_key)
            except Exception as e:
                err_str = str(e).lower()
                if any(term in err_str for term in ["429", "quota", "resourceexhausted", "rate limit", "exceeded", "limit"]):
                    print(f"[KEY_MANAGER] API Key rate-limited (attempt {attempt+1}/{max_retries}): {err_str[:120]}... Rotating key.", file=sys.stderr)
                    self.rotate_key(failed_key=current_key)
                    time.sleep(backoff)
                    backoff = min(8, backoff * 1.5)
                    last_exception = e
                else:
                    raise e
        if last_exception:
            raise last_exception

    async def aexecute_with_rotation(self, async_func, max_retries=None):
        """Async version of execute_with_rotation."""
        if max_retries is None:
            max_retries = len(self.keys) * 2 if self.keys else 1

        last_exception = None
        backoff = 1.0
        for attempt in range(max_retries):
            current_key = self.get_available_key()
            if current_key is None:
                wait = self.get_soonest_cooldown_remaining()
                print(f"[KEY_MANAGER] All keys cooling down, waiting {wait:.1f}s...", file=sys.stderr)
                await asyncio.sleep(wait + 0.5)
                current_key = self.get_api_key()

            try:
                return await async_func(current_key)
            except Exception as e:
                err_str = str(e).lower()
                if any(term in err_str for term in ["429", "quota", "resourceexhausted", "rate limit", "exceeded", "limit"]):
                    print(f"[KEY_MANAGER] Async API Key rate-limited (attempt {attempt+1}/{max_retries}): {err_str[:120]}... Rotating key.", file=sys.stderr)
                    self.rotate_key(failed_key=current_key)
                    await asyncio.sleep(backoff)
                    backoff = min(8, backoff * 1.5)
                    last_exception = e
                else:
                    raise e
        if last_exception:
            raise last_exception

key_manager = KeyManager()
