import os
import sys
import requests
import subprocess

async def check_for_update(page, status_text, progress_bar, quick_update):
    # Use sys._MEIPASS for version.txt if running as a bundled app
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
    local_version = None
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            local_version = f.read().strip()
    else:
        local_version = "unknown"

    try:
        api_url = "https://api.github.com/repos/TheDoctor200/NuphillionLauncher/releases/latest"
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        latest = resp.json()
        latest_version = latest.get("tag_name", "").lstrip("vV")
    except Exception as ex:
        status_text.value = f"Could not check latest version: {ex}"
        progress_bar.value = 0.0
        quick_update()
        return

    if local_version == latest_version:
        status_text.value = "You are currently on the latest launcher version"
        progress_bar.value = 1.0
        quick_update()
        return

    status_text.value = f"New version available: {latest_version} (current: {local_version})"
    progress_bar.value = 0.5
    quick_update()

    def open_url_hidden(url):
        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                f'start "" "{url}"',
                shell=True,
                creationflags=CREATE_NO_WINDOW
            )
        else:
            import webbrowser
            webbrowser.open(url)

    def on_select(choice):
        page.dialog.open = False
        quick_update()
        if choice == "yes":
            status_text.value = "Downloading new version..."
            quick_update()
            open_url_hidden("https://github.com/TheDoctor200/NuphillionLauncher/releases/latest")
        else:
            status_text.value = "Update cancelled."
            quick_update()

    import flet as ft
    page.dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Update Available"),
        content=ft.Text("Would you like to download the new version now?"),
        actions=[
            ft.TextButton("Yes", on_click=lambda e: on_select("yes")),
            ft.TextButton("No", on_click=lambda e: on_select("no")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.dialog.open = True
    page.update()
