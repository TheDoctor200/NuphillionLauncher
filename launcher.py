import flet as ft
import os
import shutil
import requests
import zipfile
import asyncio
import io
import sys
import time
import collections
from concurrent.futures import ThreadPoolExecutor
from mod_cache import ModCache
from offline_package_generator import OfflinePackageGenerator

# Constants
VERSION = '1_11_2931_2'
VERSION_PTR = '1_11_2931_10'
RELEASE_URI = 'https://github.com/CutesyThrower12/Nuphillion/releases/download/vInDev/nuphillion.zip'
OG_FILES_URL = 'https://github.com/CutesyThrower12/HW2-Original-Files/releases/download/1.0/hw2ogfiles.zip'
HW2_HOGAN_PATH = "Packages\\Microsoft.HoganThreshold_8wekyb3d8bbwe\\LocalState"
UPDATER_RELEASE_URL = "https://github.com/TheDoctor200/NuphillionLauncher/releases/latest/download/NuphillionLauncher.exe"

appData = os.environ.get('LOCALAPPDATA')
if not appData:
    raise RuntimeError("Unable to find LOCALAPPDATA.")


class ModManager:
    def __init__(self, appData):
        self.localStateDir = os.path.join(appData, HW2_HOGAN_PATH)
        self.version = VERSION
        if os.path.isdir(self.localPkgDir(VERSION_PTR)):
            self.version = VERSION_PTR
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Initialize mod cache
        cache_dir = os.path.join(appData, "NuphillionCache")
        self.mod_cache = ModCache(cache_dir)
        
        # Initialize offline package generator
        self.offline_generator = OfflinePackageGenerator(cache_dir)
        
        # Track current mode (online/offline)
        self.offline_mode = False

    def localPkgDir(self, version=None):
        return os.path.join(self.localStateDir, f"GTS\\{version or self.version}_active")

    def localPkgPath(self):
        return os.path.join(self.localPkgDir(), 'NuphillionMod.pkg')

    def localManifestPath(self):
        return os.path.join(self.localPkgDir(), f"{self.version}_file_manifest.xml")

    def local_mod_exists(self):
        return os.path.isfile(self.localPkgPath()) and os.path.isfile(self.localManifestPath())

    def ensure_directories(self):
        """Ensure all required directories exist"""
        os.makedirs(self.localStateDir, exist_ok=True)
        gts_path = os.path.join(self.localStateDir, "GTS")
        os.makedirs(gts_path, exist_ok=True)
        os.makedirs(self.localPkgDir(), exist_ok=True)

    def mod_cleanup(self):
        """Clean up and prepare directories for mod installation"""
        try:
            self.ensure_directories()
            target_dir = self.localPkgDir()
            if os.path.isdir(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"Directory creation error: {e}")
            raise

    async def _download_file(self, url):
        try:
            response = await asyncio.get_running_loop().run_in_executor(
                self._executor,
                lambda: requests.get(url, timeout=10, stream=True)
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Download error: {e}")
            return None

    async def install_mod(self, progress_callback, offline=False):
        try:
            self.ensure_directories()
            progress_callback(0)
            
            # Check if update is available
            mod_name = "nuphillion"
            remote_info = self.mod_cache.get_remote_version_info(RELEASE_URI)
            
            cached_file = self.mod_cache.get_cached_file_path(mod_name)
            use_cache = False
            
            # Determine which package to use
            if offline:
                # Generate offline package if it doesn't exist
                if not self.offline_generator.offline_package_exists(mod_name):
                    # First ensure online version is cached
                    if not os.path.exists(cached_file):
                        content = await self._download_file(RELEASE_URI)
                        if not content:
                            return "Failed to download mod."
                        with open(cached_file, 'wb') as f:
                            f.write(content)
                        if remote_info:
                            self.mod_cache.update_cache(mod_name, remote_info)
                    
                    # Generate offline package
                    progress_callback(10)
                    try:
                        await asyncio.get_running_loop().run_in_executor(
                            self._executor,
                            self.offline_generator.create_offline_package,
                            mod_name
                        )
                    except Exception as e:
                        return f"Failed to generate offline package: {str(e)}"
                
                # Use offline package
                offline_pkg = self.offline_generator.get_package_path(mod_name, offline=True)
                with open(offline_pkg, 'rb') as f:
                    content = f.read()
                use_cache = True
                self.offline_mode = True
                progress_callback(20)
            else:
                # Online mode - use regular cached file or download
                self.offline_mode = False
                if os.path.exists(cached_file) and not self.mod_cache.is_update_available(mod_name, remote_info):
                    use_cache = True
                    with open(cached_file, 'rb') as f:
                        content = f.read()
                    progress_callback(20)
                else:
                    content = await self._download_file(RELEASE_URI)
                    if not content:
                        return "Failed to download mod."
                    
                    self.mod_cache.cleanup_old_versions(mod_name, keep_current=False)
                    
                    with open(cached_file, 'wb') as f:
                        f.write(content)
                    
                    if remote_info:
                        self.mod_cache.update_cache(mod_name, remote_info)
                    
                    progress_callback(20)

            self.mod_cleanup()
            with zipfile.ZipFile(io.BytesIO(content)) as mod_zip:
                # Get only .pkg and .xml files
                files_to_extract = [f for f in mod_zip.namelist() 
                                  if f.endswith('.pkg') or f.endswith('.xml')]
                
                if not files_to_extract:
                    return "Invalid mod package: No valid files found"

                total_files = len(files_to_extract)
                for i, name in enumerate(files_to_extract):
                    # Map files to correct names
                    if name.endswith('.pkg'):
                        target_path = self.localPkgPath()
                    else:
                        target_path = self.localManifestPath()

                    # Extract file
                    with mod_zip.open(name) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    progress = 20 + int((i + 1) / total_files * 80)
                    progress_callback(progress)

            if not self.local_mod_exists():
                return "Installation failed: Files not properly installed"

            result_msg = f"Mod installation complete! ({'Offline' if offline else 'Online'} mode)"
            if use_cache:
                result_msg += " (Used cached version)"
            return result_msg
            
        except Exception as e:
            print(f"Installation error: {e}")
            return f"Installation failed: {str(e)}"

    async def restore_original_files(self, progress_callback, offline=False):
        try:
            progress_callback(0)
            
            # Check cache for original files
            mod_name = "hw2_original"
            remote_info = self.mod_cache.get_remote_version_info(OG_FILES_URL)
            
            cached_file = self.mod_cache.get_cached_file_path(mod_name)
            use_cache = False
            
            # Determine which package to use
            if offline:
                if not self.offline_generator.offline_package_exists(mod_name):
                    if not os.path.exists(cached_file):
                        content = await self._download_file(OG_FILES_URL)
                        if not content:
                            return "Failed to download original files."
                        with open(cached_file, 'wb') as f:
                            f.write(content)
                        if remote_info:
                            self.mod_cache.update_cache(mod_name, remote_info)
                    
                    progress_callback(10)
                    try:
                        await asyncio.get_running_loop().run_in_executor(
                            self._executor,
                            self.offline_generator.create_offline_package,
                            mod_name
                        )
                    except Exception as e:
                        return f"Failed to generate offline package: {str(e)}"
                
                offline_pkg = self.offline_generator.get_package_path(mod_name, offline=True)
                with open(offline_pkg, 'rb') as f:
                    content = f.read()
                use_cache = True
                self.offline_mode = True
                progress_callback(20)
            else:
                self.offline_mode = False
                if os.path.exists(cached_file) and not self.mod_cache.is_update_available(mod_name, remote_info):
                    use_cache = True
                    with open(cached_file, 'rb') as f:
                        content = f.read()
                    progress_callback(20)
                else:
                    content = await self._download_file(OG_FILES_URL)
                    if not content:
                        return "Failed to download original files."
                    
                    self.mod_cache.cleanup_old_versions(mod_name, keep_current=False)
                    
                    with open(cached_file, 'wb') as f:
                        f.write(content)
                    
                    if remote_info:
                        self.mod_cache.update_cache(mod_name, remote_info)
                    
                    progress_callback(20)
            
            # ...existing restore code...
            self.mod_cleanup()
            with zipfile.ZipFile(io.BytesIO(content)) as og_zip:
                total_files = len(og_zip.namelist())
                for i, member in enumerate(og_zip.infolist()):
                    if member.is_dir():
                        continue
                    target_path = os.path.join(self.localPkgDir(), os.path.basename(member.filename))
                    with og_zip.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
                    progress = 20 + int((i + 1) / total_files * 80)
                    progress_callback(progress)

            result_msg = f"Original files restored successfully! ({'Offline' if offline else 'Online'} mode)"
            if use_cache:
                result_msg += " (Used cached version)"
            return result_msg
            
        except Exception as e:
            print(f"Restore error: {e}")
            return f"Restore failed: {str(e)}"


mod_manager = ModManager(appData)

# Use absolute imports for local modules for script/flet build compatibility
from win_utils import get_aumid, launch_app
from update_utils import check_for_update
from social_utils import SOCIAL_LINKS, open_social_links_section
from launch_game_utils import launch_game_click

def main(page: ft.Page):
    page.title = "Nuphillion Mod Manager"
    page.window_title = "Nuphillion Mod Manager"
    page.window_resizable = True
    page.window_center = True
    page.window_maximizable = True
    page.window_always_on_top = False
    page.bgcolor = "#006064"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 0

    # Use sys._MEIPASS for asset paths if running as a bundled app
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    bg_path = os.path.join(ASSETS_DIR, "holo_table.jpg")
    icon_path = os.path.join(ASSETS_DIR, "The_Vanquished.png")
    favicon_path = os.path.join(ASSETS_DIR, "favicon.ico")
    VERSION_FILE = os.path.join(BASE_DIR, "version.txt")

    # Set window icon, app icon, and tray icon (if supported)
    if os.path.exists(favicon_path):
        page.window_icon = favicon_path
        page.icon = favicon_path
        try:
            page.tray_icon = favicon_path  # For Flet >=0.14.0, sets Windows tray/taskbar icon
        except Exception:
            pass

    # Get background image size
    # Dynamically determine background image size, fallback to 1920x1080 if not available
    bg_width, bg_height = 1500, 844  # fallback default
    if os.path.exists(bg_path):
        try:
            from PIL import Image
            with Image.open(bg_path) as img:
                bg_width, bg_height = img.size
        except Exception:
            pass
    if os.path.exists(bg_path):
        try:
            from PIL import Image
            with Image.open(bg_path) as img:
                bg_width, bg_height = img.size
        except Exception:
            pass

    page.window_width = bg_width
    page.window_height = bg_height

    # Dynamic background image that always covers the full app background and resizes with window
    class DynamicBg(ft.Stack):
        def __init__(self):
            super().__init__()
            self.bg_img = ft.Image(
                src=bg_path,
                fit=ft.ImageFit.COVER,
                opacity=0.5,
                width=page.window_width,
                height=page.window_height
            )
            self.controls = [self.bg_img]

        def resize(self, width, height):
            self.bg_img.width = width
            self.bg_img.height = height
            self.update()  # Update the entire container, not just the image

    status_quote = ft.Text("Manage your Nuphillion mod install with ease", color="white", size=14, italic=True)
    status_label = ft.Text("Status:", color="white", size=18, weight="bold")
    progress_bar = ft.ProgressBar(width=500, value=0, color="#97E9E6")
    status_text = ft.Text("", color="white", size=16)

    # --- Bandwidth Graph State ---
    bandwidth_history = collections.deque(maxlen=60)  # last 60 samples (seconds)
    bandwidth_chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=[],
                stroke_width=3,
                color=ft.Colors.CYAN,  # Updated to Colors
                curved=True,
                stroke_cap_round=True,
            )
        ],
        min_y=0,
        max_y=10,
        width=300,
        height=80,
        left_axis=ft.ChartAxis(labels_size=30),
        bottom_axis=ft.ChartAxis(labels_size=20),
        tooltip_bgcolor=ft.Colors.BLUE_GREY_900,  # Updated to Colors
        expand=True,
        animate=True,
    )

    # --- Bandwidth State ---
    bandwidth_value = [0.0]  # Store last bandwidth in MB/s
    size_text = ft.Text("Downloaded: 0 MB", color="white", size=15)
    bandwidth_text = ft.Text("Speed: 0.00 MB/s", color="white", size=15)
    stats_label = ft.Text("Download Statistics:", color="white", size=16, weight="bold")

    # --- Download/Install/Uninstall cancellation state ---
    install_task = {"task": None, "cancel_event": None}
    
    # Track offline mode state
    offline_mode_state = {"enabled": False}

    # --- Responsive sizing for small displays ---
    def get_responsive_sizes():
        """Get responsive sizes based on window dimensions"""
        window_width = page.window_width or 1200
        window_height = page.window_height or 800
        
        # Determine if we're on a small display
        is_small_display = window_width < 1000 or window_height < 700
        
        if is_small_display:
            return {
                'button_width': 200,
                'button_height': 45,
                'title_size': 20,
                'quote_size': 12,
                'status_size': 14,
                'progress_width': 400,
                'stats_width': 180,
                'preview_width': 150,
                'preview_height': 100,
                'icon_size': 60,
                'content_padding': 40,
                'stats_top': 120,
                'social_top': 400
            }
        else:
            return {
                'button_width': 250,
                'button_height': 50,
                'title_size': 24,
                'quote_size': 14,
                'status_size': 16,
                'progress_width': 500,
                'stats_width': 220,
                'preview_width': 180,
                'preview_height': 120,
                'icon_size': 80,
                'content_padding': 80,
                'stats_top': 150,
                'social_top': 470
            }

    # Define quick_update early so all functions can use it
    def quick_update():
        status_text.update()
        progress_bar.update()
        size_text.update()
        bandwidth_text.update()

    async def install_mod_click(e):
        # Cancel any previous install if running
        if install_task["task"] and not install_task["task"].done():
            install_task["cancel_event"].set()
            await install_task["task"]

        cancel_event = asyncio.Event()
        install_task["cancel_event"] = cancel_event

        # Reset download statistics to zero
        size_text.value = "Downloaded: 0 MB"
        bandwidth_text.value = "Speed: 0.00 MB/s"
        quick_update()

        mode_text = "offline" if offline_mode_state["enabled"] else "online"
        status_text.value = f"Installing mod ({mode_text} mode)..."
        progress_bar.value = 0
        quick_update()

        last_time = [time.time()]
        last_bytes = [0]
        total_bytes = [0]

        async def download_file_with_bandwidth(url, callback):
            loop = asyncio.get_running_loop()
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 8192
                last_graph_update = time.time()
                with io.BytesIO() as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if cancel_event.is_set():
                            return None  # Abort download
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            total_bytes[0] = downloaded
                            size_text.value = f"Downloaded: {downloaded / 1024 / 1024:.2f} MB"
                            now = time.time()
                            elapsed = now - last_time[0]
                            if elapsed > 0.5:
                                bandwidth = (downloaded - last_bytes[0]) / elapsed / 1024 / 1024
                                bandwidth_value[0] = bandwidth
                                bandwidth_text.value = f"Speed: {bandwidth:.2f} MB/s"
                                last_time[0] = now
                                last_bytes[0] = downloaded
                            quick_update()
                            await loop.run_in_executor(None, callback, chunk, total, downloaded)
                    size_text.value = f"Downloaded: {downloaded / 1024 / 1024:.2f} MB"
                    bandwidth_text.value = f"Speed: {bandwidth_value[0]:.2f} MB/s"
                    quick_update()
                    return f.getvalue()

        def progress_callback(value):
            progress_bar.value = value / 100
            quick_update()

        async def do_install():
            # Patch ModManager to use our custom downloader for bandwidth tracking
            async def patched_download_file(url):
                return await download_file_with_bandwidth(url, lambda *_: None)
            old_download_file = mod_manager._download_file
            mod_manager._download_file = patched_download_file

            result = await mod_manager.install_mod(progress_callback, offline=offline_mode_state["enabled"])
            if cancel_event.is_set():
                status_text.value = "Installation cancelled."
            else:
                status_text.value = result
            mod_manager._download_file = old_download_file
            quick_update()

        install_task["task"] = asyncio.create_task(do_install())
        await install_task["task"]

    async def uninstall_mod_click(e):
        # If install is running, cancel it and wait for it to finish before uninstalling
        if install_task["task"] and not install_task["task"].done():
            install_task["cancel_event"].set()
            await install_task["task"]

        size_text.value = "Downloaded: 0 MB"
        bandwidth_text.value = "Speed: 0.00 MB/s"
        quick_update()

        mode_text = "offline" if offline_mode_state["enabled"] else "online"
        status_text.value = f"Restoring original files ({mode_text} mode)..."
        progress_bar.value = 0
        quick_update()
        def progress_callback(value):
            progress_bar.value = value / 100
            quick_update()
        result = await mod_manager.restore_original_files(progress_callback, offline=offline_mode_state["enabled"])
        status_text.value = result
        quick_update()

    async def update_app_click(e):
        await check_for_update(page, status_text, progress_bar, quick_update)

    async def check_status_click(e):
        if mod_manager.local_mod_exists():
            status_text.value = "Mod is installed and up-to-date!" if mod_manager.version == VERSION else "Mod is outdated. Update available."
            progress_bar.value = 1.0
        else:
            status_text.value = "Mod is not installed."
            progress_bar.value = 0.0
        quick_update()

    def open_discord(e):
        import webbrowser
        webbrowser.open("https://discord.gg/NeTyqrvbeY")

    def toggle_offline_mode(e):
        """Toggle between online and offline mode"""
        offline_mode_state["enabled"] = not offline_mode_state["enabled"]
        mode = "Offline" if offline_mode_state["enabled"] else "Online"
        status_text.value = f"Switched to {mode} mode"
        
        # Update button text
        e.control.text = f"Mode: {mode}"
        e.control.bgcolor = "#FF6F00" if offline_mode_state["enabled"] else "#4CAF50"
        quick_update()

    def create_button(text, on_click, color, icon=None):
        sizes = get_responsive_sizes()
        return ft.ElevatedButton(
            text,
            on_click=on_click,
            bgcolor=color,
            color="white",
            width=sizes['button_width'],
            height=sizes['button_height'],
            icon=icon,
            icon_color="white" if icon else None
        )

    # Define the async handler before using it in create_button
    async def launch_game_click_handler(e):
        await launch_game_click(
            e,
            status_text=status_text,
            progress_bar=progress_bar,
            quick_update=quick_update,
            page=page
        )

    # Get responsive sizes for initial setup
    sizes = get_responsive_sizes()
    
    # Update text elements with responsive sizing
    status_quote = ft.Text("Manage your Nuphillion mod install with ease", color="white", size=sizes['quote_size'], italic=True)
    status_label = ft.Text("Status:", color="white", size=18, weight="bold")
    progress_bar = ft.ProgressBar(width=sizes['progress_width'], value=0, color="#97E9E6")
    status_text = ft.Text("", color="white", size=sizes['status_size'])

    buttons = ft.Column([
        create_button("Install Mod", install_mod_click, "#00796B", ft.Icons.DOWNLOAD),
        create_button("Uninstall Mod", uninstall_mod_click, "#D32F2F", ft.Icons.DELETE_FOREVER),
        create_button("Mode: Online", toggle_offline_mode, "#4CAF50", ft.Icons.WIFI),
        create_button("Check Status", check_status_click, "#1976D2", ft.Icons.INFO),
        create_button("Update Launcher", update_app_click, "#FF9800", ft.Icons.UPGRADE),
        create_button("Open Discord", open_discord, "#6200EE", ft.Icons.CHAT),
    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    # Center UI elements vertically and horizontally
    content = ft.Container(
        content=ft.Column([
            ft.Text(
                "Nuphillion Mod Manager",
                size=sizes['title_size'],
                weight="bold",
                color="white",
                text_align=ft.TextAlign.CENTER,
            ),
            status_quote,
            ft.Container(status_label, padding=ft.padding.only(top=24)),
            status_text,
            progress_bar,
            ft.Container(buttons, padding=ft.padding.only(top=8)),
            ft.Container(
                ft.Text("Developed by CutesyThrower12 and TheDoctor :)", size=12, color="white"),
                padding=ft.padding.only(top=10)
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=sizes['content_padding']),
    )

    stack_children = []
    if os.path.exists(bg_path):
        dynamic_bg = DynamicBg()
        stack_children.append(dynamic_bg)
        def on_resize(e):
            # Update responsive sizing when window is resized
            global sizes
            sizes = get_responsive_sizes()
            
            # Update UI elements with new sizes
            status_quote.size = sizes['quote_size']
            status_text.size = sizes['status_size']
            progress_bar.width = sizes['progress_width']
            
            # Update content container padding
            content.padding = ft.padding.only(top=sizes['content_padding'])
            
            # Update icon size if it exists
            if icon:
                icon.content.width = sizes['icon_size']
                icon.content.height = sizes['icon_size']
            
            # Update stats container positioning and sizing
            for child in stack_children:
                if hasattr(child, 'left') and child.left == 20:  # Stats container
                    child.top = sizes['stats_top']
                    child.width = sizes['stats_width']
                    # Update preview image size
                    for col_child in child.content.controls:
                        if hasattr(col_child, 'content') and hasattr(col_child.content, 'width'):
                            if col_child.content.width == sizes['preview_width']:  # Preview image
                                col_child.content.width = sizes['preview_width']
                                col_child.content.height = sizes['preview_height']
                                break
            
            # Update social links positioning
            for child in stack_children:
                if hasattr(child, 'left') and child.left == 20 and hasattr(child, 'top') and child.top == sizes['social_top']:
                    child.top = sizes['social_top']
                    break
            
            # Update button sizes
            for button in buttons.controls:
                button.width = sizes['button_width']
                button.height = sizes['button_height']
            
            # Update title size
            for child in content.content.controls:
                if hasattr(child, 'size') and child.size == sizes['title_size']:
                    child.size = sizes['title_size']
                    break
            
            dynamic_bg.resize(page.window_width, page.window_height)
            page.update()  # Force the app to update on every resize
        page.on_resize = on_resize  # Ensures background resizes with window

    # Prepare icon if exists (ensure 'icon' is always defined)
    icon = None
    if os.path.exists(icon_path):
        icon = ft.Container(
            content=ft.Image(
                src=icon_path,
                width=sizes['icon_size'],
                height=sizes['icon_size'],
                fit=ft.ImageFit.CONTAIN,
            ),
            alignment=ft.alignment.top_left,
            padding=20,
        )

    stack_children.append(content)
    if icon:
        stack_children.append(icon)
        
        # Use GIF for preview (simpler and more reliable than video)
        video_widget = ft.Image(
            src=os.path.join(ASSETS_DIR, "HaloWars2Preview.gif"),
            width=sizes['preview_width'],
            height=sizes['preview_height'],
            fit=ft.ImageFit.COVER,
        )
        
        # Add bandwidth and size info under the icon (top left) with mica style
        stack_children.append(
            ft.Container(
                content=ft.Column([
                    stats_label,
                    size_text,
                    bandwidth_text,
                    ft.Container(
                        create_button("Launch Game", launch_game_click_handler, "#43A047", ft.Icons.PLAY_ARROW),
                        padding=ft.padding.only(top=10)
                    ),
                    ft.Container(
                        content=video_widget,
                        width=sizes['preview_width'],
                        height=sizes['preview_height'],
                        border_radius=18,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        padding=ft.padding.only(top=10, bottom=0),
                    )
                ], spacing=6),
                left=20,
                top=sizes['stats_top'],
                width=sizes['stats_width'],
                bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLUE_GREY_900),
                border_radius=16,
                blur=20,
                shadow=ft.BoxShadow(
                    blur_radius=16,
                    color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                    spread_radius=2,
                    offset=ft.Offset(2, 4)
                ),
                padding=16,
            )
        )
    
    # Social links (below the stats/info box, separated by a divider)
    stack_children.append(
        open_social_links_section(ASSETS_DIR, left=20, top=sizes['social_top'])
    )

    page.add(
        ft.Stack([
            *stack_children,
        ])
    )

ft.app(target=main)