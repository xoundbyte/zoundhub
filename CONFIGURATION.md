# Spotify API Configuration

This project uses the Spotify Web API to fetch artist metadata. To use the Spotify integration, you need to configure API credentials.

## Getting Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create app"
4. Fill in the app details:
   - **App name**: zoundhub (or any name you prefer)
   - **App description**: Artist metadata aggregator
   - **Redirect URI**: http://localhost:8888/callback (not used, but required)
5. Accept the terms and create the app
6. Click on your new app, then "Settings"
7. Copy the **Client ID** and **Client Secret**

## Configuration

### Option 1: Environment Variables (Recommended for local development)

```bash
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
```

### Option 2: GitHub Secrets (For GitHub Actions)

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click "New repository secret"
4. Add two secrets:
   - Name: `SPOTIFY_CLIENT_ID` | Value: your client ID
   - Name: `SPOTIFY_CLIENT_SECRET` | Value: your client secret

## Usage

### Processing Artists

```python
from spotify_client import SpotifyAPI

# Initialize with environment variables
spotify = SpotifyAPI()

# Or pass credentials directly
spotify = SpotifyAPI(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Search for an artist
artist = spotify.search_artist("The Beatles")

# Get artist details
details = spotify.get_artist(artist["id"])

# Get top tracks
tracks = spotify.get_artist_top_tracks(artist["id"])
```

### Running the Processor

```bash
python process_artists.py
```

This will process up to 5 artists from the queue, respecting Spotify's rate limits.

## Rate Limiting

Spotify's API has rate limits. This implementation:
- Processes 5 artists per run (configurable)
- Waits 1 second between requests
- Handles 429 (rate limit) responses gracefully
- GitHub Actions runs every 4 hours to stay within limits

## Security Notes

- Never commit your credentials to the repository
- The GitHub Action uses repository secrets for secure credential storage
- You can revoke credentials at any time by deleting the app from your Spotify Developer Dashboard
- Credentials are only used for read-only API calls (searching and fetching artist data)