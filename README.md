# Heatwave Monitor - Indian Cities

A simple Tkinter + SQLite desktop app showing monthly weather for 96 Indian cities (2020-2025).

## Files
- `main.py` - window and the 5 tabs (Dashboard, City Data, Heat Months, Summary, Charts)
- `database.py` - all SQL code and the heat rule
- `popular_cities_weather.csv` - dataset (keep it in the same folder)
- `heatwave.db` - created automatically on first run

## How to run
1. Install Python 3.10 or newer (Tkinter is included).
2. Open a terminal in this folder and install matplotlib:
   ```
   pip install -r requirements.txt
   ```
3. Start the app:
   ```
   python main.py
   ```
On first run the CSV is imported into `heatwave.db` (wspd column dropped, duplicates skipped, empty values stored as NULL).

## Heat rule (monthly max temperature)
| tmax | Level |
|---|---|
| >= 43 °C | Severe heat |
| >= 40 °C | Heatwave-prone |
| >= 37 °C | Hot |
| below 37 °C | Normal |

Simplified threshold, not the official IMD daily heatwave criteria.

## Charts tab
Pick a chart type from the dropdown: line, grouped bar, rainfall bar, histogram,
box plot, scatter, pie, area (min-max range) and a two-city comparison.
