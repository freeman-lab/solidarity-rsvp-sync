import time
import requests


BASE_URL = 'https://api.solidarity.tech/v1'
PAGE_SIZE = 100


class TokenBucket:
    """60 requests per 30s window with bursting, per Solidarity's documented limit."""

    def __init__(self, capacity=60, refill_per_sec=2.0):
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.tokens = float(capacity)
        self.last = time.monotonic()

    def acquire(self):
        while True:
            now = time.monotonic()
            self.tokens = min(
                self.capacity,
                self.tokens + (now - self.last) * self.refill_per_sec,
            )
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            time.sleep((1 - self.tokens) / self.refill_per_sec)


class SolidarityClient:
    def __init__(self, token, logger=None, max_retries=3):
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
        )
        self.bucket = TokenBucket()
        self.logger = logger or (lambda s: None)
        self.max_retries = max_retries

    def get(self, path, params=None):
        url = f'{BASE_URL}{path}'
        attempt = 0
        while True:
            self.bucket.acquire()
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                if attempt >= self.max_retries:
                    raise
                backoff = 2**attempt
                self.logger(f'network error: {e}; retrying in {backoff}s')
                time.sleep(backoff)
                attempt += 1
                continue

            if resp.status_code == 429:
                wait = int(resp.headers.get('Retry-After', '30'))
                self.logger(f'429 throttled; waiting {wait}s')
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                if attempt >= self.max_retries:
                    resp.raise_for_status()
                backoff = 2**attempt
                self.logger(f'{resp.status_code} from API; retrying in {backoff}s')
                time.sleep(backoff)
                attempt += 1
                continue

            resp.raise_for_status()
            return resp.json()

    def count_rsvps(self, event_id, session_id=None):
        """Page through /event_rsvps and return total count.

        meta.total_count reflects the current page, not the full result set,
        so we walk pages until we get a short one and sum the lengths.
        """
        params = {
            'event_id': event_id,
            '_limit': PAGE_SIZE,
            '_offset': 0,
            'full_user_payload': 'false',
        }
        if session_id is not None:
            params['session_id'] = session_id

        total = 0
        while True:
            payload = self.get('/event_rsvps', params=params)
            rows = payload.get('data', [])
            total += len(rows)
            if len(rows) < PAGE_SIZE:
                return total
            params['_offset'] += PAGE_SIZE
