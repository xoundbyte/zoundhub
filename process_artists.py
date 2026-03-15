import os
import json
import time
from datetime import datetime
from spotify_client import SpotifyAPI, SpotifyRateLimitError

ARTISTS_QUEUE_FILE = "artists_queue.json"
PROCESSED_FILE = "processed_artists.json"
BATCH_SIZE = 5

def load_json_file(filepath, default=None):
    """Load JSON file or return default if not exists."""
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else []

def save_json_file(filepath, data):
    """Save data to JSON file."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def process_artists():
    """Process a batch of artists from the queue."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
        return 1
    
    try:
        spotify = SpotifyAPI(client_id, client_secret)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    queue = load_json_file(ARTISTS_QUEUE_FILE, [])
    processed = load_json_file(PROCESSED_FILE, [])
    processed_ids = {p["id"] for p in processed}
    
    # Filter already processed artists
    pending = [a for a in queue if a.get("id") not in processed_ids]
    
    if not pending:
        print("No pending artists to process")
        return 0
    
    batch = pending[:BATCH_SIZE]
    print(f"Processing {len(batch)} artists (batch size: {BATCH_SIZE})")
    
    for artist in batch:
        artist_id = artist.get("id")
        artist_name = artist.get("name", "Unknown")
        
        print(f"Processing: {artist_name} (ID: {artist_id})")
        
        try:
            # Fetch artist details from Spotify
            details = spotify.get_artist(artist_id)
            
            if details:
                artist_data = {
                    "id": artist_id,
                    "name": details.get("name"),
                    "genres": details.get("genres", []),
                    "popularity": details.get("popularity"),
                    "followers": details.get("followers", {}).get("total"),
                    "spotify_url": details.get("external_urls", {}).get("spotify"),
                    "images": details.get("images", []),
                    "processed_at": datetime.now().isoformat()
                }
                
                # Fetch top tracks
                try:
                    top_tracks = spotify.get_artist_top_tracks(artist_id)
                    artist_data["top_tracks"] = [
                        {
                            "name": t.get("name"),
                            "popularity": t.get("popularity"),
                            "preview_url": t.get("preview_url")
                        }
                        for t in top_tracks[:5]
                    ]
                except SpotifyRateLimitError:
                    pass
                
                # Fetch albums
                try:
                    albums = spotify.get_artist_albums(artist_id, limit=10)
                    artist_data["albums"] = [
                        {
                            "name": a.get("name"),
                            "release_date": a.get("release_date"),
                            "total_tracks": a.get("total_tracks")
                        }
                        for a in albums
                    ]
                except SpotifyRateLimitError:
                    pass
                
                processed.append(artist_data)
                print(f"  ✓ Processed: {artist_data['name']}")
            else:
                # Artist not found, mark as processed to skip
                processed.append({
                    "id": artist_id,
                    "name": artist_name,
                    "error": "Artist not found on Spotify",
                    "processed_at": datetime.now().isoformat()
                })
                print(f"  ✗ Artist not found on Spotify")
            
            # Small delay to be respectful to the API
            time.sleep(1)
            
        except SpotifyRateLimitError as e:
            print(f"  ✗ Rate limited. Retry after {e.retry_after}s")
            break
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    save_json_file(PROCESSED_FILE, processed)
    
    remaining = len(pending) - len(batch)
    print(f"\nBatch complete. Processed: {len(batch)}, Remaining: {remaining}")
    return 0

if __name__ == "__main__":
    exit(process_artists())