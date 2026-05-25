# Arcadia 5000 Weather Terminal

Retro-future Tkinter weather terminal with live city search, Open-Meteo weather data, map/radar display, sponsored ad slides, local Ollama-generated weather briefings, music, and sound effects.

## Quick Start

```bash
git clone <your-github-repo-url>
cd arcadia-weather-terminal

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

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

## Notes For Sharing

This repository includes visual/audio/font assets inside `assets/`, so teammates do not need the original `/Users/.../Downloads` paths. If the repository will be public, confirm that every included asset is allowed to be redistributed.
