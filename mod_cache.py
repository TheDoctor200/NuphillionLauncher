import os
import json
import requests
import glob
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

class ModCache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "mod_cache.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"User-Agent": "NuphillionLauncher/1.3"})

    def load_cache(self):
        """Load cached mod information"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_cache(self, cache_data):
        """Save mod cache information"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except IOError:
            print("Error: Could not write to cache file.")

    def _parse_release_url(self, url):
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 6 and parts[2:4] == ["releases", "download"]:
            owner, repo = parts[0], parts[1]
            # The tag can be 'latest' or a specific version
            tag = parts[4]
            asset_name = parts[-1]
            return owner, repo, tag, asset_name
        return None, None, None, None

    def _build_signature(self, metadata):
        if not metadata:
            return None
        # A stable signature based on immutable asset properties from GitHub API
        fields = (
            metadata.get("asset_id"),
            metadata.get("asset_updated_at"),
            metadata.get("asset_size"),
        )
        if not any(fields):
            return None
        return "|".join(str(value or "") for value in fields)

    def get_remote_version_info(self, url):
        owner, repo, tag, asset_name = self._parse_release_url(url)
        if not owner:
            print(f"Could not parse GitHub URL: {url}")
            return None

        # If tag is 'vInDev', it's not a stable release, so we check the 'latest' endpoint to see if it matches.
        # However, the URL points to a specific tag, so we should query that tag.
        # For now, let's assume the tag in the URL is the one we want.
        api_tag = "latest" if tag == "vInDev" else f"tags/{tag}"
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/{api_tag}"
        
        try:
            resp = self.session.get(
                api_url,
                timeout=15,
                headers={"Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
            release = resp.json() or {}
        except requests.exceptions.ConnectionError as e:
            print(f"Network connection error: {e}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"Request timeout: {e}")
            return None
        except requests.RequestException as e:
            print(f"GitHub API request failed: {e}")
            return None

        for asset in release.get("assets", []):
            # Match by asset name or the full download URL
            if asset.get("name") == asset_name or asset.get("browser_download_url") == url:
                metadata = {
                    "download_url": asset.get("browser_download_url"),
                    "tag": release.get("tag_name"),
                    "asset_id": asset.get("id"),
                    "asset_size": asset.get("size"),
                    "asset_updated_at": asset.get("updated_at"),
                }
                metadata["signature"] = self._build_signature(metadata)
                return metadata
        
        print(f"Asset '{asset_name}' not found in release '{tag}'.")
        return None

    def is_update_available(self, mod_name, remote_info):
        """Check if a mod update is available based on cached metadata."""
        cache = self.load_cache()
        
        # If not in cache, update is "available" (needs download)
        if mod_name not in cache:
            print(f"Mod {mod_name} not in cache metadata")
            return True
        
        # If we can't get remote info, check if cached file actually exists
        if not remote_info or not remote_info.get("signature"):
            cached_file = self.get_cached_file_path(mod_name)
            if not os.path.exists(cached_file):
                print(f"Remote info unavailable and cached file missing for {mod_name}")
                return True
            # File exists and we can't check remote, assume current
            print(f"Using existing cache for {mod_name} (remote unavailable)")
            return False
            
        cached_info = cache[mod_name]
        if not cached_info.get("signature"):
            print(f"Old cache format for {mod_name}, forcing update")
            return True # Old cache format, force update.

        is_different = remote_info["signature"] != cached_info["signature"]
        if is_different:
            print(f"Signature mismatch for {mod_name}")
        return is_different
    
    def update_cache(self, mod_name, remote_info):
        """Update cache with new mod info"""
        if not remote_info or not remote_info.get("signature"):
            return
        cache = self.load_cache()
        cache[mod_name] = remote_info
        self.save_cache(cache)
    
    def get_cached_file_path(self, mod_name):
        """Get the path to cached mod file"""
        return os.path.join(self.cache_dir, f"{mod_name}.zip")
    
    def cleanup_old_versions(self, mod_name, keep_current=True):
        """Delete old cached versions of a mod"""
        try:
            # Get pattern for this mod's cached files
            pattern = os.path.join(self.cache_dir, f"{mod_name}*.zip")
            old_files = glob.glob(pattern)
            
            current_file = self.get_cached_file_path(mod_name)
            
            for old_file in old_files:
                # Skip the current version if keep_current is True
                if keep_current and os.path.normpath(old_file) == os.path.normpath(current_file):
                    continue
                
                try:
                    os.remove(old_file)
                    print(f"Deleted old cache: {old_file}")
                except Exception as e:
                    print(f"Failed to delete {old_file}: {e}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def get_cache_size(self):
        """Get total size of cache directory in MB"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            print(f"Error calculating cache size: {e}")
        return total_size / (1024 * 1024)  # Convert to MB
