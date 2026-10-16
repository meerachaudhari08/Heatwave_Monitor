"""database.py - all SQLite code for Heatwave Monitor. The GUI never writes SQL."""
import csv
import os
import sqlite3

# File locations (same folder as this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "popular_cities_weather.csv")
DB_FILE = os.path.join(BASE_DIR, "heatwave.db")

# Heat rule based on monthly maximum temperature (checked from top to bottom)
HEAT_LEVELS = [
    (43, "Severe heat"),
    (40, "Heatwave-prone"),
    (37, "Hot"),
]
NORMAL = "Normal"


def heat_level(tmax):
    """Return the heat level text for a tmax value."""
    if tmax is None:
        return "-"
    for limit, name in HEAT_LEVELS:
        if tmax >= limit:
            return name
    return NORMAL


def min_tmax_for_level(level_name):
    """Return the lowest tmax that counts as the given heat level."""
    for limit, name in HEAT_LEVELS:
        if name == level_name:
            return limit
    return None


def get_connection():
    return sqlite3.connect(DB_FILE)


def to_float(value):
    """Convert a CSV value to float, or None if it is empty."""
    value = value.strip()
    return float(value) if value else None


def setup_database():
    """Create the table and import the CSV if the table is empty."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            date TEXT NOT NULL,
            year INTEGER,
            month INTEGER,
            tavg REAL, tmin REAL, tmax REAL,
            prcp REAL, pres REAL, tsun REAL,
            UNIQUE(city, date)
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_city ON weather_data(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_year ON weather_data(year)")

    cur.execute("SELECT COUNT(*) FROM weather_data")
    if cur.fetchone()[0] == 0:
        if not os.path.exists(CSV_FILE):
            conn.close()
            raise FileNotFoundError(CSV_FILE)
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                date = row["date"][:10]  # keep only YYYY-MM-DD
                # INSERT OR IGNORE skips duplicate (city, date) rows; wspd is dropped
                cur.execute(
                    """INSERT OR IGNORE INTO weather_data
                       (city, date, year, month, tavg, tmin, tmax, prcp, pres, tsun)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["city"].strip(), date, int(date[:4]), int(date[5:7]),
                     to_float(row["tavg"]), to_float(row["tmin"]), to_float(row["tmax"]),
                     to_float(row["prcp"]), to_float(row["pres"]), to_float(row["tsun"])))
        conn.commit()
    conn.close()


def get_cities():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT city FROM weather_data ORDER BY city").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT year FROM weather_data ORDER BY year").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_city_data(city, year=None):
    """Rows of (date, tavg, tmin, tmax, prcp, pres) for one city."""
    sql = "SELECT date, tavg, tmin, tmax, prcp, pres FROM weather_data WHERE city = ?"
    params = [city]
    if year is not None:
        sql += " AND year = ?"
        params.append(year)
    sql += " ORDER BY date"
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_heat_months(min_level, year=None):
    """Rows of (city, date, tmax) at or above a heat level, hottest first."""
    sql = "SELECT city, date, tmax FROM weather_data WHERE tmax >= ?"
    params = [min_tmax_for_level(min_level)]
    if year is not None:
        sql += " AND year = ?"
        params.append(year)
    sql += " ORDER BY tmax DESC"
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_city_summary(city):
    """Return a dict with summary numbers for one city."""
    conn = get_connection()
    cur = conn.cursor()
    hottest = cur.execute(
        "SELECT date, tmax FROM weather_data WHERE city = ? AND tmax IS NOT NULL "
        "ORDER BY tmax DESC LIMIT 1", (city,)).fetchone()
    count40 = cur.execute(
        "SELECT COUNT(*) FROM weather_data WHERE city = ? AND tmax >= 40", (city,)).fetchone()[0]
    avg_tmax, avg_prcp = cur.execute(
        "SELECT AVG(tmax), AVG(prcp) FROM weather_data WHERE city = ?", (city,)).fetchone()
    conn.close()
    return {"hottest": hottest, "months_40": count40,
            "avg_tmax": avg_tmax, "avg_prcp": avg_prcp}


def get_tmax_series(city):
    """Rows of (date, tmax) for the chart."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT date, tmax FROM weather_data WHERE city = ? AND tmax IS NOT NULL ORDER BY date",
        (city,)).fetchall()
    conn.close()
    return rows


def get_top_hottest_cities(limit=5):
    """Cities with the highest tmax ever recorded."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT city, MAX(tmax) AS m FROM weather_data GROUP BY city "
        "ORDER BY m DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


# ---------- Functions for the Dashboard and Charts tabs ----------

def get_overview():
    """Overall numbers for the dashboard."""
    conn = get_connection()
    cur = conn.cursor()
    total, cities, years, avg_tmax = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT city), COUNT(DISTINCT year), AVG(tmax) "
        "FROM weather_data").fetchone()
    hottest = cur.execute(
        "SELECT city, date, tmax FROM weather_data WHERE tmax IS NOT NULL "
        "ORDER BY tmax DESC LIMIT 1").fetchone()
    hot40 = cur.execute("SELECT COUNT(*) FROM weather_data WHERE tmax >= 40").fetchone()[0]
    conn.close()
    return {"total": total, "cities": cities, "years": years,
            "avg_tmax": avg_tmax, "hottest": hottest, "months_40": hot40}


def get_heat_level_counts(city=None):
    """Count of months in each heat level (all cities, or one city)."""
    sql = "SELECT tmax FROM weather_data WHERE tmax IS NOT NULL"
    params = []
    if city:
        sql += " AND city = ?"
        params.append(city)
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    counts = {NORMAL: 0}
    for _, name in HEAT_LEVELS:
        counts[name] = 0
    for (t,) in rows:
        counts[heat_level(t)] += 1
    return counts


def get_yearly_avg_tmax():
    """Average tmax of all cities for each year."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT year, AVG(tmax) FROM weather_data GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return rows


def get_heat_months_per_year():
    """Number of city-months with tmax >= 40 for each year."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT year, SUM(CASE WHEN tmax >= 40 THEN 1 ELSE 0 END) "
        "FROM weather_data GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return rows


def get_monthly_avg(city):
    """Average tmax, tmin and rainfall for each calendar month (1-12) of a city."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT month, AVG(tmax), AVG(tmin), AVG(prcp) FROM weather_data "
        "WHERE city = ? GROUP BY month ORDER BY month", (city,)).fetchall()
    conn.close()
    return rows


def get_city_column(city, column):
    """All non-empty values of one column for a city, with date and year."""
    allowed = ("tavg", "tmin", "tmax", "prcp", "pres")
    if column not in allowed:  # column names cannot be parameters, so check them
        raise ValueError("Unknown column")
    conn = get_connection()
    rows = conn.execute(
        f"SELECT date, year, {column} FROM weather_data "
        f"WHERE city = ? AND {column} IS NOT NULL ORDER BY date", (city,)).fetchall()
    conn.close()
    return rows


def get_tmax_prcp(city):
    """(tmax, prcp) pairs for a scatter plot."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tmax, prcp FROM weather_data WHERE city = ? "
        "AND tmax IS NOT NULL AND prcp IS NOT NULL", (city,)).fetchall()
    conn.close()
    return rows
