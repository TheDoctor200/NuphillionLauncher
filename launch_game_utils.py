from win_utils import get_aumid, launch_app

async def launch_game_click(e, status_text=None, progress_bar=None, quick_update=None, page=None):
    """
    Launches the game and updates the UI.
    Expects status_text, progress_bar, quick_update, and page to be passed from the main UI.
    """
    try:
        app_name = "Halo Wars 2"
        aumid = get_aumid(app_name)
        if aumid:
            launch_app(aumid)
            if status_text is not None:
                status_text.value = f"Game launched! ({aumid})"
            if progress_bar is not None:
                progress_bar.value = 1.0  # Set progress bar to 100%
        else:
            if status_text is not None:
                status_text.value = f"Could not find app with name '{app_name}'"
            if progress_bar is not None:
                progress_bar.value = 0.0  # Set progress bar to 0%
    except Exception as ex:
        if status_text is not None:
            status_text.value = f"Failed to launch game: {ex}"
        if progress_bar is not None:
            progress_bar.value = 0.0  # Set progress bar to 0%
    if quick_update is not None:
        quick_update()
    if page is not None:
        page.update()
