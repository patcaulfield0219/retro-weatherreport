# Project Structure

## `main.py`

The app is currently kept in one file so it is easy to run during presentations. The file is organized into major sections:

- `Config`: window size, asset paths, colors, API URLs, timing, and saved settings.
- `WeatherData`: Open-Meteo city search, weather fetches, regional observations, radar profile, and Ollama text generation.
- `AudioController`: background music, startup sound, and interface sound effects.
- `SlideRenderer`: shared Canvas drawing helpers.
- Slide classes: each screen of the broadcast, such as current weather, briefing, hourly timeline, ads, observations, forecast, radar, and credits.
- `RetroCastApp`: Tkinter window, boot screen, city search, progress bar, slide rotation, refresh logic, and controls.

## Helper Scripts

- `check_setup.py`: verifies Python packages, key assets, Open-Meteo access, and optional Ollama availability.
- `run_macos.command`: one-click macOS launcher that creates/uses `.venv`, installs packages, and runs the app.
- `run_windows.bat`: one-click Windows launcher with the same setup flow.

## Asset Paths

All bundled assets are loaded relative to `main.py`:

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
```

This is what lets teammates clone the project anywhere and run it without editing local paths.

## Future Refactor Ideas

If the project becomes larger, split `main.py` into:

- `config.py`
- `weather_data.py`
- `audio.py`
- `slides/`
- `app.py`

For the current report/demo version, the single-file structure is safer and easier for teammates to run.
