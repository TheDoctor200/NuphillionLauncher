import flet as ft
import os
import subprocess
import sys

# Define your social links here
SOCIAL_LINKS = [
    ("ModDB", "https://www.moddb.com/members/thedoctor18", "moddb.png"),
    ("YouTube", "https://www.youtube.com/@thedoctor199", "youtube.png"),
    ("Discord", "https://discord.com/invite/8sa3f6ZpJk", "discord.png"),
    ("GitHub", "https://github.com/TheDoctor200", "github.png"),  # <-- GitHub entry
]

def open_social_link(url):
    # Always open browser window hidden (no console)
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

def open_social_links_section(assets_dir, left=20, top=470):
    # Returns a Flet Container with the social links section
    return ft.Container(
        content=ft.Column([
            ft.Container(
                ft.Text(
                    "TheDoctors Socials:",
                    size=15,
                    weight="bold",
                    color="white",
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.center_left,
                padding=ft.padding.only(right=8),
            ),
            ft.Divider(height=24, thickness=2, color="#97E9E6"),
            ft.Row(
                [
                    # Build each social button with fallback when image is missing
                    ft.Column(
                        [
                            # ... create button with image if exists else an IconButton ...
                            (lambda name=name, url=url, icon=icon: ft.Column(
                                [
                                    (
                                        ft.IconButton(
                                            icon=ft.Icons.CODE,  # fallback icon
                                            tooltip=name,
                                            on_click=lambda e, u=url: open_social_link(u),
                                            style=ft.ButtonStyle(
                                                bgcolor={"": ft.Colors.with_opacity(0.35, ft.Colors.BLUE_GREY_900)},
                                                shape=ft.RoundedRectangleBorder(radius=12),
                                            ),
                                            icon_size=28
                                        )
                                        if not os.path.exists(os.path.join(assets_dir, icon))
                                        else ft.IconButton(
                                            content=ft.Image(
                                                src=os.path.join(assets_dir, icon),
                                                width=32,
                                                height=32,
                                                fit=ft.ImageFit.CONTAIN,
                                            ),
                                            tooltip=name,
                                            on_click=lambda e, u=url: open_social_link(u),
                                            style=ft.ButtonStyle(
                                                bgcolor={"": ft.Colors.with_opacity(0.35, ft.Colors.BLUE_GREY_900)},
                                                shape=ft.RoundedRectangleBorder(radius=12),
                                            ),
                                        )
                                    ),
                                    ft.Text(
                                        name,
                                        size=12,
                                        color="white",
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ))()
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    for name, url, icon in SOCIAL_LINKS
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=8,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.END,
        ),
        left=left,
        top=top,
        width=220,
        bgcolor=None,
        border_radius=None,
        blur=None,
        shadow=None,
        padding=0,
    )
