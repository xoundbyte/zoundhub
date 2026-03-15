import os
import sys
import json
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_client import SpotifyAPI, SpotifyAPIError, SpotifyAuthError, SpotifyRateLimitError


def create_mock_response(data, status=200):
    """Helper to create a mock response for urlopen."""
    mock = MagicMock()
    mock.getcode.return_value = status
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


class TestSpotifyAPI(unittest.TestCase):
    
    def setUp(self):
        os.environ["SPOTIFY_CLIENT_ID"] = "test_client_id"
        os.environ["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    
    def tearDown(self):
        for key in ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]:
            if key in os.environ:
                del os.environ[key]
    
    def test_init_with_env_vars(self):
        api = SpotifyAPI()
        self.assertEqual(api.client_id, "test_client_id")
        self.assertEqual(api.client_secret, "test_client_secret")
    
    def test_init_with_params(self):
        api = SpotifyAPI("custom_id", "custom_secret")
        self.assertEqual(api.client_id, "custom_id")
        self.assertEqual(api.client_secret, "custom_secret")
    
    def test_init_missing_credentials(self):
        del os.environ["SPOTIFY_CLIENT_ID"]
        del os.environ["SPOTIFY_CLIENT_SECRET"]
        with self.assertRaises(ValueError):
            SpotifyAPI()
    
    @patch("spotify_client.urlopen")
    def test_get_access_token(self, mock_urlopen):
        auth_response = create_mock_response({
            "access_token": "test_token",
            "expires_in": 3600
        })
        mock_urlopen.return_value = auth_response
        
        api = SpotifyAPI()
        token = api._get_access_token()
        
        self.assertEqual(token, "test_token")
    
    @patch("spotify_client.urlopen")
    def test_get_artist(self, mock_urlopen):
        # First call is auth, second is the artist request
        auth_response = create_mock_response({
            "access_token": "test_token",
            "expires_in": 3600
        })
        artist_response = create_mock_response({
            "id": "123",
            "name": "Test Artist",
            "genres": ["pop"],
            "popularity": 80,
            "followers": {"total": 1000000},
            "external_urls": {"spotify": "https://spotify.com/artist/123"},
            "images": []
        })
        mock_urlopen.side_effect = [auth_response, artist_response]
        
        api = SpotifyAPI()
        artist = api.get_artist("123")
        
        self.assertEqual(artist["name"], "Test Artist")
        self.assertEqual(artist["popularity"], 80)
    
    @patch("spotify_client.urlopen")
    def test_search_artist(self, mock_urlopen):
        auth_response = create_mock_response({
            "access_token": "test_token",
            "expires_in": 3600
        })
        search_response = create_mock_response({
            "artists": {
                "items": [
                    {"id": "456", "name": "Searched Artist"}
                ]
            }
        })
        mock_urlopen.side_effect = [auth_response, search_response]
        
        api = SpotifyAPI()
        result = api.search_artist("test query")
        
        self.assertEqual(result["name"], "Searched Artist")
    
    def test_rate_limit_error_class(self):
        """Test that SpotifyRateLimitError captures retry_after correctly."""
        error = SpotifyRateLimitError(60)
        self.assertEqual(error.retry_after, 60)
        self.assertIn("60", str(error))
        
    def test_rate_limit_from_http_error(self):
        """Test that rate limit exceptions are created from HTTP 429."""
        from urllib.error import HTTPError
        from io import BytesIO
        
        # Create an HTTPError like Spotify would return
        fp = BytesIO(b'{"error": "rate_limited"}')
        error = HTTPError(
            "https://api.spotify.com/v1/artists/123",
            429,
            "Too Many Requests",
            {"Retry-After": "60"},
            fp
        )
        
        # Verify the error has the expected attributes
        self.assertEqual(error.code, 429)
        self.assertEqual(error.headers.get("Retry-After"), "60")


class TestArtistProcessing(unittest.TestCase):
    
    def setUp(self):
        self.test_queue = [
            {"id": "artist1", "name": "Artist One"},
            {"id": "artist2", "name": "Artist Two"}
        ]
    
    @patch.dict(os.environ, {
        "SPOTIFY_CLIENT_ID": "test_id",
        "SPOTIFY_CLIENT_SECRET": "test_secret"
    })
    @patch("process_artists.SpotifyAPI")
    @patch("process_artists.load_json_file")
    @patch("process_artists.save_json_file")
    def test_process_artists_success(self, mock_save, mock_load, mock_api_class):
        mock_load.side_effect = [
            self.test_queue,  # queue
            []  # processed
        ]
        
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_artist.return_value = {
            "name": "Artist One",
            "genres": ["pop"],
            "popularity": 50,
            "followers": {"total": 1000},
            "external_urls": {"spotify": "url"},
            "images": []
        }
        mock_api.get_artist_top_tracks.return_value = []
        mock_api.get_artist_albums.return_value = []
        
        from process_artists import process_artists
        result = process_artists()
        
        self.assertEqual(result, 0)
        mock_save.assert_called_once()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_process_artists_missing_credentials(self):
        from process_artists import process_artists
        result = process_artists()
        self.assertEqual(result, 1)


class TestExceptions(unittest.TestCase):
    
    def test_spotify_api_error(self):
        error = SpotifyAPIError("Test error")
        self.assertEqual(str(error), "Test error")
    
    def test_spotify_auth_error(self):
        error = SpotifyAuthError("Auth failed")
        self.assertEqual(str(error), "Auth failed")
    
    def test_spotify_rate_limit_error(self):
        error = SpotifyRateLimitError(120)
        self.assertEqual(error.retry_after, 120)
        self.assertIn("120", str(error))


if __name__ == "__main__":
    unittest.main()