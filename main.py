from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from collections import defaultdict
import re
from typing import List, Dict, Tuple, Set
import time

SCOPES = ['https://www.googleapis.com/auth/youtube']

class YouTubePlaylistManager:
    def __init__(self):
        """Initialize the YouTube API client with authentication."""
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes=SCOPES)
        self.creds = flow.run_local_server(port=8080)
        self.youtube = build('youtube', 'v3', credentials=self.creds)
        self.MAX_VIDEOS_PER_PLAYLIST = 5000
        
    def get_all_playlists(self) -> List[Dict]:
        """Get all playlists owned by the authenticated user."""
        playlists = []
        next_page_token = None
        
        try:
            while True:
                request = self.youtube.playlists().list(
                    part='snippet,contentDetails',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                playlists.extend(response['items'])
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                    
        except HttpError as e:
            print(f"Error fetching playlists: {e}")
            return []
            
        return playlists
    
    def get_playlist_videos(self, playlist_id: str) -> List[Dict]:
        """Get all videos in a specific playlist."""
        videos = []
        next_page_token = None
        
        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                videos.extend(response['items'])
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                    
        except HttpError as e:
            print(f"Error fetching videos for playlist {playlist_id}: {e}")
            return []
            
        return videos
    
    def find_duplicate_playlists(self, playlists: List[Dict]) -> List[List[Dict]]:
        """Find playlists that might be duplicates based on name similarity."""
        # Group playlists by normalized name
        normalized_groups = defaultdict(list)
        
        for playlist in playlists:
            # Skip Watch Later playlist
            if playlist['snippet']['title'].lower() == 'watch later':
                continue
                
            # Normalize playlist name (remove common words, lowercase, etc.)
            normalized_name = self._normalize_playlist_name(playlist['snippet']['title'])
            normalized_groups[normalized_name].append(playlist)
        
        # Return groups with more than one playlist
        duplicates = [group for group in normalized_groups.values() if len(group) > 1]
        return duplicates
    
    def _normalize_playlist_name(self, name: str) -> str:
        """Normalize playlist name for comparison."""
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove common words that don't add meaning
        common_words = ['playlist', 'videos', 'music', 'songs', 'collection', 'mix', 'favorites', 'liked']
        for word in common_words:
            normalized = normalized.replace(word, '')
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def merge_playlists(self, source_playlists: List[Dict], target_playlist: Dict) -> bool:
        """Merge videos from source playlists into the target playlist."""
        try:
            all_videos = set()
            
            # Collect all unique video IDs from source playlists
            for playlist in source_playlists:
                videos = self.get_playlist_videos(playlist['id'])
                for video in videos:
                    video_id = video['contentDetails']['videoId']
                    all_videos.add(video_id)
            
            # Get existing videos in target playlist to avoid duplicates
            target_videos = self.get_playlist_videos(target_playlist['id'])
            existing_video_ids = {video['contentDetails']['videoId'] for video in target_videos}
            
            # Add only new videos to target playlist
            new_videos = all_videos - existing_video_ids
            
            # Check if we'll exceed the 5000 video limit
            total_videos_after_merge = len(target_videos) + len(new_videos)
            if total_videos_after_merge > self.MAX_VIDEOS_PER_PLAYLIST:
                print(f"⚠️  Warning: Merging would result in {total_videos_after_merge} videos (limit: {self.MAX_VIDEOS_PER_PLAYLIST})")
                print("Only the first videos that fit within the limit will be added.")
                # Limit the number of new videos to add
                max_new_videos = self.MAX_VIDEOS_PER_PLAYLIST - len(target_videos)
                new_videos = list(new_videos)[:max_new_videos]
            
            added_count = 0
            for video_id in new_videos:
                try:
                    self.youtube.playlistItems().insert(
                        part='snippet',
                        body={
                            'snippet': {
                                'playlistId': target_playlist['id'],
                                'resourceId': {
                                    'kind': 'youtube#video',
                                    'videoId': video_id
                                }
                            }
                        }
                    ).execute()
                    added_count += 1
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.1)
                except HttpError as e:
                    print(f"Error adding video {video_id}: {e}")
                    continue
            
            print(f"Successfully merged {added_count} videos into '{target_playlist['snippet']['title']}'")
            return True
            
        except HttpError as e:
            print(f"Error merging playlists: {e}")
            return False
    
    def auto_merge_all_duplicates(self, playlists: List[Dict]) -> Dict:
        """Automatically merge all duplicate playlists intelligently."""
        duplicates = self.find_duplicate_playlists(playlists)
        results = {
            'merged_groups': 0,
            'deleted_playlists': 0,
            'errors': []
        }
        
        if not duplicates:
            print("✅ No duplicates found to merge!")
            return results
        
        print(f"🤖 Starting automatic merge of {len(duplicates)} duplicate groups...")
        
        for i, group in enumerate(duplicates, 1):
            print(f"\n--- Processing Group {i}/{len(duplicates)} ---")
            
            # Sort by video count (keep the one with most videos as target)
            group.sort(key=lambda p: p['contentDetails']['itemCount'], reverse=True)
            target = group[0]
            sources = group[1:]
            
            print(f"Target: {target['snippet']['title']} ({target['contentDetails']['itemCount']} videos)")
            print(f"Sources: {len(sources)} playlists to merge")
            
            # Check if target playlist is near the limit
            target_video_count = target['contentDetails']['itemCount']
            if target_video_count >= self.MAX_VIDEOS_PER_PLAYLIST:
                print(f"⚠️  Target playlist is at limit ({target_video_count} videos). Skipping this group.")
                results['errors'].append(f"Group {i}: Target playlist at limit")
                continue
            
            # Merge the playlists
            if self.merge_playlists(sources, target):
                results['merged_groups'] += 1
                
                # Delete the source playlists after successful merge
                for source in sources:
                    if self.delete_playlist(source['id']):
                        results['deleted_playlists'] += 1
                        # Remove from playlists list
                        for j, playlist in enumerate(playlists):
                            if playlist['id'] == source['id']:
                                playlists.pop(j)
                                break
                    else:
                        results['errors'].append(f"Failed to delete {source['snippet']['title']}")
            else:
                results['errors'].append(f"Failed to merge group {i}")
        
        return results
    
    def move_video_between_playlists(self, video_id: str, from_playlist_id: str, to_playlist_id: str) -> bool:
        """Move a video from one playlist to another."""
        try:
            # Add to target playlist
            self.youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': to_playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            ).execute()
            
            # Remove from source playlist
            # First, find the playlist item ID
            playlist_items = self.get_playlist_videos(from_playlist_id)
            for item in playlist_items:
                if item['contentDetails']['videoId'] == video_id:
                    self.youtube.playlistItems().delete(id=item['id']).execute()
                    break
            
            return True
        except HttpError as e:
            print(f"Error moving video: {e}")
            return False
    
    def reorder_playlist_videos(self, playlist_id: str, video_positions: List[Tuple[str, int]]) -> bool:
        """Reorder videos in a playlist by moving them to specific positions."""
        try:
            for video_id, new_position in video_positions:
                # Find the current position of the video
                playlist_items = self.get_playlist_videos(playlist_id)
                current_position = None
                item_id = None
                
                for i, item in enumerate(playlist_items):
                    if item['contentDetails']['videoId'] == video_id:
                        current_position = i
                        item_id = item['id']
                        break
                
                if current_position is not None and item_id:
                    # Move the video to the new position
                    self.youtube.playlistItems().update(
                        part='snippet',
                        body={
                            'id': item_id,
                            'snippet': {
                                'playlistId': playlist_id,
                                'resourceId': {
                                    'kind': 'youtube#video',
                                    'videoId': video_id
                                },
                                'position': new_position
                            }
                        }
                    ).execute()
            
            return True
        except HttpError as e:
            print(f"Error reordering videos: {e}")
            return False
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist (use with caution!)."""
        try:
            self.youtube.playlists().delete(id=playlist_id).execute()
            print(f"Successfully deleted playlist {playlist_id}")
            return True
        except HttpError as e:
            print(f"Error deleting playlist {playlist_id}: {e}")
            return False
    
    def rename_playlist(self, playlist_id: str, new_title: str) -> bool:
        """Rename a playlist."""
        try:
            self.youtube.playlists().update(
                part='snippet',
                body={
                    'id': playlist_id,
                    'snippet': {
                        'title': new_title
                    }
                }
            ).execute()
            print(f"Successfully renamed playlist to '{new_title}'")
            return True
        except HttpError as e:
            print(f"Error renaming playlist: {e}")
            return False
    
    def display_playlists(self, playlists: List[Dict]):
        """Display all playlists in a formatted way."""
        print("\n=== YOUR YOUTUBE PLAYLISTS ===")
        for i, playlist in enumerate(playlists, 1):
            title = playlist['snippet']['title']
            video_count = playlist['contentDetails']['itemCount']
            status = "⚠️  FULL" if video_count >= self.MAX_VIDEOS_PER_PLAYLIST else "✅ OK"
            print(f"{i:2d}. {title} ({video_count} videos) {status}")
    
    def display_duplicates(self, duplicates: List[List[Dict]]):
        """Display found duplicate playlists."""
        if not duplicates:
            print("\n✅ No duplicate playlists found!")
            return
        
        print(f"\n🔍 Found {len(duplicates)} groups of potential duplicates:")
        for i, group in enumerate(duplicates, 1):
            print(f"\nGroup {i}:")
            for playlist in group:
                title = playlist['snippet']['title']
                video_count = playlist['contentDetails']['itemCount']
                print(f"  - {title} ({video_count} videos)")

def main():
    """Main function to run the playlist management tool."""
    print("🎵 YouTube Playlist Manager")
    print("=" * 40)
    
    # Initialize the manager
    manager = YouTubePlaylistManager()
    
    # Get all playlists
    print("Fetching your playlists...")
    playlists = manager.get_all_playlists()
    
    if not playlists:
        print("No playlists found or error occurred.")
        return
    
    # Display all playlists
    manager.display_playlists(playlists)
    
    # Find duplicates
    print("\nAnalyzing for duplicates...")
    duplicates = manager.find_duplicate_playlists(playlists)
    manager.display_duplicates(duplicates)
    
    # Mode selection
    print("\n" + "=" * 40)
    print("Select Mode:")
    print("1. 🤖 Automatic Mode - Smart merge all duplicates")
    print("2. 🎮 Manual Mode - Control each operation")
    print("3. 📊 Analysis Only - Just show what needs to be done")
    
    mode_choice = input("\nEnter mode (1-3): ").strip()
    
    if mode_choice == '1':
        # Automatic mode
        print("\n🤖 AUTOMATIC MODE")
        print("This will intelligently merge all duplicate playlists.")
        print("The playlist with the most videos in each group will be kept.")
        print("Source playlists will be deleted after successful merge.")
        
        confirm = input("\nProceed with automatic merge? (y/N): ").lower()
        if confirm == 'y':
            results = manager.auto_merge_all_duplicates(playlists)
            
            print(f"\n🎉 Automatic merge completed!")
            print(f"✅ Merged {results['merged_groups']} groups")
            print(f"🗑️  Deleted {results['deleted_playlists']} playlists")
            if results['errors']:
                print(f"❌ {len(results['errors'])} errors occurred:")
                for error in results['errors']:
                    print(f"   - {error}")
    
    elif mode_choice == '2':
        # Manual mode
        manual_menu(manager, playlists, duplicates)
    
    elif mode_choice == '3':
        # Analysis mode
        print("\n📊 ANALYSIS MODE")
        print("Here's what could be done:")
        
        if duplicates:
            total_videos_in_duplicates = sum(
                sum(p['contentDetails']['itemCount'] for p in group) 
                for group in duplicates
            )
            print(f"📈 Total videos in duplicate playlists: {total_videos_in_duplicates}")
            print(f"🎯 Potential space saved: {len(duplicates)} duplicate groups")
        else:
            print("✅ No duplicates found - your playlists are well organized!")
    
    else:
        print("Invalid choice!")

def manual_menu(manager: YouTubePlaylistManager, playlists: List[Dict], duplicates: List[List[Dict]]):
    """Manual mode menu with advanced controls."""
    while True:
        print("\n" + "=" * 40)
        print("🎮 MANUAL MODE - What would you like to do?")
        print("1. Merge duplicate playlists")
        print("2. Rename a playlist")
        print("3. Delete a playlist")
        print("4. Move video between playlists")
        print("5. Reorder videos in a playlist")
        print("6. Show all playlists")
        print("7. Show duplicates analysis")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            if duplicates:
                print("\nSelect a group to merge:")
                for i, group in enumerate(duplicates, 1):
                    print(f"{i}. {group[0]['snippet']['title']} (and {len(group)-1} others)")
                
                try:
                    group_choice = int(input("Enter group number: ")) - 1
                    if 0 <= group_choice < len(duplicates):
                        group = duplicates[group_choice]
                        
                        # Let user choose target playlist
                        print("\nSelect target playlist (videos will be merged into this one):")
                        for i, playlist in enumerate(group, 1):
                            print(f"{i}. {playlist['snippet']['title']} ({playlist['contentDetails']['itemCount']} videos)")
                        
                        target_choice = int(input("Enter target playlist number: ")) - 1
                        if 0 <= target_choice < len(group):
                            target = group[target_choice]
                            sources = [p for j, p in enumerate(group) if j != target_choice]
                            
                            print(f"\nMerging into: {target['snippet']['title']}")
                            print("From:")
                            for source in sources:
                                print(f"  - {source['snippet']['title']}")
                            
                            confirm = input("\nProceed with merge? (y/N): ").lower()
                            if confirm == 'y':
                                if manager.merge_playlists(sources, target):
                                    # Remove merged playlists from duplicates list
                                    duplicates.pop(group_choice)
                                    print("Merge completed!")
                                else:
                                    print("Merge failed!")
                        else:
                            print("Invalid target playlist number!")
                    else:
                        print("Invalid group number!")
                except ValueError:
                    print("Please enter a valid number!")
            else:
                print("No duplicates to merge!")
                
        elif choice == '2':
            print("\nSelect playlist to rename:")
            for i, playlist in enumerate(playlists, 1):
                print(f"{i}. {playlist['snippet']['title']}")
            
            try:
                playlist_choice = int(input("Enter playlist number: ")) - 1
                if 0 <= playlist_choice < len(playlists):
                    playlist = playlists[playlist_choice]
                    new_title = input(f"Enter new title for '{playlist['snippet']['title']}': ").strip()
                    if new_title:
                        manager.rename_playlist(playlist['id'], new_title)
                        # Update the playlist title in our list
                        playlist['snippet']['title'] = new_title
                else:
                    print("Invalid playlist number!")
            except ValueError:
                print("Please enter a valid number!")
                
        elif choice == '3':
            print("\n⚠️  WARNING: This will permanently delete the playlist!")
            print("Select playlist to delete:")
            for i, playlist in enumerate(playlists, 1):
                print(f"{i}. {playlist['snippet']['title']}")
            
            try:
                playlist_choice = int(input("Enter playlist number: ")) - 1
                if 0 <= playlist_choice < len(playlists):
                    playlist = playlists[playlist_choice]
                    if playlist['snippet']['title'].lower() == 'watch later':
                        print("❌ Cannot delete Watch Later playlist!")
                    else:
                        confirm = input(f"Are you sure you want to delete '{playlist['snippet']['title']}'? (y/N): ").lower()
                        if confirm == 'y':
                            if manager.delete_playlist(playlist['id']):
                                playlists.pop(playlist_choice)
                                print("Playlist deleted!")
                else:
                    print("Invalid playlist number!")
            except ValueError:
                print("Please enter a valid number!")
        
        elif choice == '4':
            print("\nMove video between playlists:")
            print("Select source playlist:")
            for i, playlist in enumerate(playlists, 1):
                print(f"{i}. {playlist['snippet']['title']}")
            
            try:
                source_choice = int(input("Enter source playlist number: ")) - 1
                if 0 <= source_choice < len(playlists):
                    source_playlist = playlists[source_choice]
                    videos = manager.get_playlist_videos(source_playlist['id'])
                    
                    print(f"\nVideos in '{source_playlist['snippet']['title']}':")
                    for i, video in enumerate(videos[:10], 1):  # Show first 10 videos
                        title = video['snippet']['title']
                        print(f"{i}. {title}")
                    
                    if len(videos) > 10:
                        print(f"... and {len(videos) - 10} more videos")
                    
                    video_choice = int(input("Enter video number to move: ")) - 1
                    if 0 <= video_choice < len(videos):
                        video_id = videos[video_choice]['contentDetails']['videoId']
                        
                        print("\nSelect target playlist:")
                        for i, playlist in enumerate(playlists, 1):
                            if i-1 != source_choice:  # Don't show source playlist
                                print(f"{i}. {playlist['snippet']['title']}")
                        
                        target_choice = int(input("Enter target playlist number: ")) - 1
                        if 0 <= target_choice < len(playlists) and target_choice != source_choice:
                            target_playlist = playlists[target_choice]
                            
                            if manager.move_video_between_playlists(video_id, source_playlist['id'], target_playlist['id']):
                                print("Video moved successfully!")
                            else:
                                print("Failed to move video!")
                        else:
                            print("Invalid target playlist!")
                    else:
                        print("Invalid video number!")
                else:
                    print("Invalid source playlist number!")
            except ValueError:
                print("Please enter a valid number!")
        
        elif choice == '5':
            print("\nReorder videos in a playlist:")
            print("Select playlist:")
            for i, playlist in enumerate(playlists, 1):
                print(f"{i}. {playlist['snippet']['title']}")
            
            try:
                playlist_choice = int(input("Enter playlist number: ")) - 1
                if 0 <= playlist_choice < len(playlists):
                    playlist = playlists[playlist_choice]
                    videos = manager.get_playlist_videos(playlist['id'])
                    
                    print(f"\nVideos in '{playlist['snippet']['title']}':")
                    for i, video in enumerate(videos, 1):
                        title = video['snippet']['title']
                        print(f"{i}. {title}")
                    
                    print("\nEnter new positions (e.g., '3 1' to move video 3 to position 1)")
                    print("Enter 'done' when finished:")
                    
                    reorder_commands = []
                    while True:
                        cmd = input("Enter command: ").strip()
                        if cmd.lower() == 'done':
                            break
                        
                        try:
                            parts = cmd.split()
                            if len(parts) == 2:
                                video_num = int(parts[0]) - 1
                                new_pos = int(parts[1]) - 1
                                if 0 <= video_num < len(videos) and new_pos >= 0:
                                    video_id = videos[video_num]['contentDetails']['videoId']
                                    reorder_commands.append((video_id, new_pos))
                                else:
                                    print("Invalid video number or position!")
                            else:
                                print("Please enter two numbers: video_number new_position")
                        except ValueError:
                            print("Please enter valid numbers!")
                    
                    if reorder_commands:
                        if manager.reorder_playlist_videos(playlist['id'], reorder_commands):
                            print("Videos reordered successfully!")
                        else:
                            print("Failed to reorder videos!")
                else:
                    print("Invalid playlist number!")
            except ValueError:
                print("Please enter a valid number!")
                
        elif choice == '6':
            manager.display_playlists(playlists)
            
        elif choice == '7':
            manager.display_duplicates(duplicates)
            
        elif choice == '8':
            print("Goodbye! 👋")
            break
            
        else:
            print("Invalid choice! Please enter 1-8.")

if __name__ == "__main__":
    main()
