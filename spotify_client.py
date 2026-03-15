import os
import json
import time
import base64
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

class SpotifyAPI:
    """Spotify Web API client with rate limiting support."""
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        self._access_token = None
        self._token_expires = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify client ID and secret are required")
    
    def _get_auth_header(self):
        """Create Basic Auth header for token request."""
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        return f"Basic {credentials}"
    
    def _get_access_token(self):
        """Get or refresh access token."""
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token
        
        request = Request(
            self.AUTH_URL,
            data=urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": self._get_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode())
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
                return self._access_token
        except HTTPError as e:
            error_body = e.read().decode()
            raise SpotifyAPIError(f"Authentication failed: {error_body}")
    
    def _make_request(self, endpoint, params=None):
        """Make authenticated request to Spotify API."""
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        
        request = Request(
            url,
            headers={"Authorization": f"Bearer {self._get_access_token()}"}
        )
        
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode())
        except HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 60))
                raise SpotifyRateLimitError(retry_after)
            elif e.code == 401:
                raise SpotifyAuthError("Invalid credentials or expired token")
            elif e.code == 404:
                return None
            else:
                raise SpotifyAPIError(f"HTTP {e.code}: {e.read().decode()}")
    
    def search_artist(self, query, limit=1):
        """Search for an artist by name."""
        params = {
            "q": query,
            "type": "artist",
            "limit": limit
        }
        result = self._make_request("/search", params)
        if result and result.get("artists", {}).get("items"):
            return result["artists"]["items"][0]
        return None
    
    def get_artist(self, artist_id):
        """Get artist details by Spotify ID."""
        return self._make_request(f"/artists/{artist_id}")
    
    def get_artist_top_tracks(self, artist_id, market="US"):
        """Get artist's top tracks."""
        params = {"market": market}
        result = self._make_request(f"/artists/{artist_id}/top-tracks", params)
        return result.get("tracks", []) if result else []
    
    def get_artist_albums(self, artist_id, limit=50):
        """Get artist's albums."""
        params = {"limit": limit}
        result = self._make_request(f"/artists/{artist_id}/albums", params)
        return result.get("items", []) if result else []


class SpotifyAPIError(Exception):
    """Base exception for Spotify API errors."""
    pass


class SpotifyAuthError(SpotifyAPIError):
    """Authentication-related errors."""
    pass


class SpotifyRateLimitError(SpotifyAPIError):
    """Rate limit exceeded error."""
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds")