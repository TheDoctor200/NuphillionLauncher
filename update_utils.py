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
        latest_version = latest.get("tag_name", "")
        # Ensure both local_version and latest_version are compared without leading 'v' or 'V' and dots
        def normalize_version(ver):
            ver = ver.strip()
            if ver.lower().startswith("v"):
                ver = ver[1:]
            return ver.lstrip(".")
        normalized_local_version = normalize_version(local_version)
        normalized_latest_version = normalize_version(latest_version)
    except Exception as ex:
        status_text.value = f"Could not check latest version: {ex}"
        progress_bar.value = 0.0
        quick_update()
        return

    if normalized_local_version == normalized_latest_version:
        status_text.value = "You are currently on the latest launcher version"
        progress_bar.value = 1.0
        quick_update()
        return

    status_text.value = f"New version available: {latest_version} (current: {local_version})"
    progress_bar.value = 0.5
    quick_update()

    import flet as ft

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

    def on_yes(e):
        page.overlay.clear()
        page.update()  # Ensure the overlay is removed immediately
        status_text.value = "Opening dwonload page..."
        quick_update()
        open_url_hidden("https://github.com/TheDoctor200/NuphillionLauncher/releases/latest")

    def on_no(e):
        page.overlay.clear()
        page.update()  # Ensure the overlay is removed immediately
        status_text.value = "Update cancelled."
        quick_update()

    # Create a centered modal container for the update prompt with mica style
    update_prompt = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    f"New version available: {latest_version}",
                    size=16,
                    weight="bold",
                    color="white",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"Current version: {local_version}",
                    size=13,
                    color="white",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Would you like to download the new version now?",
                    size=13,
                    color="white",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton("Yes", bgcolor=ft.colors.GREEN, color="white", on_click=on_yes),
                        ft.ElevatedButton("No", bgcolor=ft.colors.RED_400, color="white", on_click=on_no),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        width=300,
        padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
        bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLUE_GREY_900),
        border_radius=16,
        blur=20,
        shadow=ft.BoxShadow(
            blur_radius=16,
            color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
            spread_radius=2,
            offset=ft.Offset(2, 4)
        ),
        alignment=ft.alignment.center,
    )

    # Show the modal in the center of the app
    page.overlay.clear()
    page.overlay.append(
        ft.Container(
            content=update_prompt,
            alignment=ft.alignment.center,
            expand=True,
        )
    )
    page.update()
