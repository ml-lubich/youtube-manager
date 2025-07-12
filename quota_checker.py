from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

SCOPES = ['https://www.googleapis.com/auth/youtube']

def check_quota():
    """Check YouTube API quota usage."""
    print("🔍 YouTube API Quota Checker")
    print("=" * 40)
    
    try:
        # Initialize the API client
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes=SCOPES)
        creds = flow.run_local_server(port=8080)  # Different port to avoid conflicts
        youtube = build('youtube', 'v3', credentials=creds)
        
        # Try a simple API call to test quota
        print("Testing API access...")
        response = youtube.channels().list(part='snippet', mine=True).execute()
        print("✅ API is working! Quota is available.")
        
        # Get quota information
        print("\n📊 Quota Information:")
        print("- YouTube Data API v3 has a default quota of 10,000 units per day")
        print("- Different operations cost different amounts:")
        print("  • channels().list() - 1 unit")
        print("  • playlists().list() - 1 unit")
        print("  • playlistItems().list() - 1 unit")
        print("  • playlistItems().insert() - 50 units")
        print("  • playlists().delete() - 50 units")
        print("  • playlists().update() - 50 units")
        
        print("\n💡 Tips to manage quota:")
        print("1. Wait until tomorrow for quota reset")
        print("2. Use the Analysis mode first (fewer API calls)")
        print("3. Batch operations to reduce total calls")
        print("4. Consider upgrading to a paid Google Cloud account")
        
    except HttpError as e:
        if "quotaExceeded" in str(e):
            print("❌ Quota exceeded! You've used up your daily API quota.")
            print("\n🕐 Solutions:")
            print("1. Wait until tomorrow (quota resets daily)")
            print("2. Check your quota usage in Google Cloud Console")
            print("3. Consider upgrading your Google Cloud account")
        else:
            print(f"❌ API Error: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_quota() 