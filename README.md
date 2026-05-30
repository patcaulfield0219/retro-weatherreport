# Arcadia 5000 Weather Terminal

Retro-future Tkinter weather terminal with live city search, Open-Meteo weather data, map/radar display, sponsored ad slides, local Ollama-generated weather briefings, music, and sound effects.

## Quick Start

```bash
git clone https://github.com/patcaulfield0219/retro-weatherreport.git
cd retro-weatherreport

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

macOS users can also double-click:

```text
run_macos.command
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Windows users can also double-click:

```text
run_windows.bat
```

## Setup Check

If the app does not open, run:

```bash
python3 check_setup.py
```

This checks Python, required packages, bundled assets, Open-Meteo access, and whether Ollama is running.

## Optional Local Text Generation

The weather briefing page works without Ollama, but it will show a red `OLLAMA SUMMARY OFFLINE` warning and use a local fallback summary.

To enable local generated summaries:

```bash
ollama pull llama3.2
ollama serve
```

Then run:

```bash
python3 main.py
```

## Project Layout

```text
arcadia-weather-terminal/
├─ main.py
├─ check_setup.py
├─ run_macos.command
├─ run_windows.bat
├─ requirements.txt
├─ config.example.json
├─ assets/
│  ├─ audio/
│  ├─ fonts/
│  ├─ ads/
│  └─ logos/
└─ docs/
   └─ PROJECT_STRUCTURE.md
```

## Data Sources

- Weather and city search: Open-Meteo APIs
- Map tiles: OpenStreetMap
- Rain radar overlay: RainViewer public map API
- Local generated text: Ollama running on `localhost:11434`

## Configuration

The app creates `retro_weather_config.json` automatically when settings are saved. That file is ignored by Git because it is local to each user.

Use `config.example.json` as a reference if a teammate wants to reset or document their local settings.

## Demo Controls

- `PAUSE`: pause the automatic slide rotation for presentation.
- `RESUME`: continue automatic rotation.
- `PREV` / `NEXT`: manually move between pages.
- `REFRESH`: fetch weather data again.
- `CITY` + `GO`: search and lock a new city.
- `MUSIC` / `SFX`: toggle background music and interface sounds.

## Screenshots

Add presentation screenshots to:

```text
docs/screenshots/
```

Recommended screenshots:

- Startup city search
- Current Conditions
- Corporate Weather Brief
- Hourly Timeline
- Live Map Radar
- Sponsored Corporate Message

## Troubleshooting

### `ModuleNotFoundError`

Run:

```bash
pip install -r requirements.txt
```

### Windows PowerShell blocks virtual environment activation

Run PowerShell as the current user and execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### `OLLAMA SUMMARY OFFLINE`

The app still works. To enable generated briefings:

```bash
ollama pull llama3.2
ollama serve
```

### No music or sound effects

Run:

```bash
pip install pygame
```

Then restart the app.

### Tkinter window does not open

Make sure your Python install includes Tkinter. On macOS, the official Python installer from python.org usually includes it.

## Notes For Sharing

This repository includes visual/audio/font assets inside `assets/`, so teammates do not need the original `/Users/.../Downloads` paths. If the repository will be public, confirm that every included asset is allowed to be redistributed.
