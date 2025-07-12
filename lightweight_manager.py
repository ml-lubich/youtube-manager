from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from collections import defaultdict
import re
from typing import List, Dict

SCOPES = ['https://www.googleapis.com/auth/youtube']

class LightweightPlaylistManager:
    def __init__(self):
        """Initialize with minimal API calls."""
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes=SCOPES)
        self.creds = flow.run_local_server(port=8080)  # Different port
        self.youtube = build('youtube', 'v3', credentials=self.creds)
        
    def get_playlists_only(self) -> List[Dict]:
        """Get only playlist metadata (minimal API calls)."""
        try:
            request = self.youtube.playlists().list(
                part='snippet,contentDetails',
                mine=True,
                maxResults=50  # Get first 50 playlists only
            )
            response = request.execute()
            return response.get('items', [])
        except HttpError as e:
            print(f"Error fetching playlists: {e}")
            return []
    
    def find_duplicates_by_name(self, playlists: List[Dict]) -> List[List[Dict]]:
        """Find duplicates using only playlist names (no video fetching)."""
        normalized_groups = defaultdict(list)
        
        for playlist in playlists:
            if playlist['snippet']['title'].lower() == 'watch later':
                continue
                
            normalized_name = self._normalize_name(playlist['snippet']['title'])
            normalized_groups[normalized_name].append(playlist)
        
        return [group for group in normalized_groups.values() if len(group) > 1]
    
    def _normalize_name(self, name: str) -> str:
        """Simple name normalization."""
        normalized = name.lower()
        common_words = ['playlist', 'videos', 'music', 'songs', 'collection', 'mix', 'favorites', 'liked']
        for word in common_words:
            normalized = normalized.replace(word, '')
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def display_analysis(self, playlists: List[Dict], duplicates: List[List[Dict]]):
        """Display analysis without making additional API calls."""
        print("\n📊 PLAYLIST ANALYSIS (Lightweight Mode)")
        print("=" * 50)
        
        print(f"📁 Total Playlists: {len(playlists)}")
        
        # Count videos (from metadata only)
        total_videos = sum(p['contentDetails']['itemCount'] for p in playlists)
        print(f"🎬 Total Videos: {total_videos}")
        
        # Find large playlists
        large_playlists = [p for p in playlists if p['contentDetails']['itemCount'] > 1000]
        print(f"📈 Large Playlists (>1000 videos): {len(large_playlists)}")
        
        # Find empty playlists
        empty_playlists = [p for p in playlists if p['contentDetails']['itemCount'] == 0]
        print(f"📭 Empty Playlists: {len(empty_playlists)}")
        
        if duplicates:
            print(f"\n🔍 Duplicate Groups Found: {len(duplicates)}")
            total_duplicate_videos = sum(
                sum(p['contentDetails']['itemCount'] for p in group) 
                for group in duplicates
            )
            print(f"🎯 Videos in Duplicates: {total_duplicate_videos}")
            print(f"💾 Potential Space Saved: {len(duplicates)} groups")
            
            print("\n📋 Duplicate Groups:")
            for i, group in enumerate(duplicates, 1):
                print(f"\nGroup {i}:")
                for playlist in group:
                    title = playlist['snippet']['title']
                    count = playlist['contentDetails']['itemCount']
                    print(f"  • {title} ({count} videos)")
        else:
            print("\n✅ No duplicate playlists found!")
        
        if empty_playlists:
            print(f"\n🗑️  Empty Playlists (can be safely deleted):")
            for playlist in empty_playlists:
                print(f"  • {playlist['snippet']['title']}")

def main():
    """Lightweight playlist analysis."""
    print("🎵 Lightweight YouTube Playlist Manager")
    print("=" * 50)
    print("💡 This mode uses minimal API calls to save quota")
    
    manager = LightweightPlaylistManager()
    
    print("\nFetching playlist metadata...")
    playlists = manager.get_playlists_only()
    
    if not playlists:
        print("No playlists found or quota exceeded.")
        return
    
    print(f"Found {len(playlists)} playlists")
    
    # Find duplicates
    duplicates = manager.find_duplicates_by_name(playlists)
    
    # Display analysis
    manager.display_analysis(playlists, duplicates)
    
    print("\n" + "=" * 50)
    print("💡 Next Steps:")
    print("1. Wait for quota reset tomorrow to use full features")
    print("2. Use Analysis mode in main.py when quota is available")
    print("3. Consider upgrading Google Cloud account for higher quotas")

if __name__ == "__main__":
    main() 