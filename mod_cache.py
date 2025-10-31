import os
import json
import hashlib
import requests

class ModCache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "mod_cache.json")
        os.makedirs(cache_dir, exist_ok=True)
        
    def load_cache(self):
        """Load cached mod information"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self, cache_data):
        """Save mod cache information"""
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def get_remote_version_info(self, url):
        """Get version info from GitHub release"""
        try:
            # Extract repo info from URL
            if "github.com" in url:
                parts = url.split("/")
                owner = parts[3]
                repo = parts[4]
                api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                
                resp = requests.get(api_url, timeout=10)
                resp.raise_for_status()
                release_data = resp.json()
                
                return {
                    "tag": release_data.get("tag_name"),
                    "published_at": release_data.get("published_at"),
                    "download_url": url
                }
        except:
            pass
        return None
    
    def is_update_available(self, mod_name, remote_info):
        """Check if a mod update is available"""
        cache = self.load_cache()
        
        if mod_name not in cache:
            return True
        
        cached_info = cache[mod_name]
        
        # Compare versions/timestamps
        if remote_info and cached_info.get("tag") != remote_info.get("tag"):
            return True
        
        if remote_info and cached_info.get("published_at") != remote_info.get("published_at"):
            return True
            
        return False
    
    def update_cache(self, mod_name, remote_info):
        """Update cache with new mod info"""
        cache = self.load_cache()
        cache[mod_name] = remote_info
        self.save_cache(cache)
    
    def get_cached_file_path(self, mod_name):
        """Get the path to cached mod file"""
        return os.path.join(self.cache_dir, f"{mod_name}.zip")
