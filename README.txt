Accutech Environmental Monitoring Dashboard

1. Install Python 3.10 or newer.
2. Open Command Prompt in this folder.
3. Run: pip install -r requirements.txt
4. Run: streamlit run app.py
5. Upload the CSV. Download separate or combined PDF reports.

CSV expected columns in order:
Timestamp ; Temperature (deg C) ; Relative Humidity (%) ; Relative Air Pressure (hPa)
Header row optional. Dates in US month/day/year format.

The PDF uses a close visual reproduction of the provided Network Data-Logger charts.
