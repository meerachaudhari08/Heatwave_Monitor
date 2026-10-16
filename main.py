"""main.py - window and tabs for Heatwave Monitor - Indian Cities."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database as db

FONT = "Segoe UI"
BG = "#f4f4f4"
NOTE = ("Based on monthly maximum temperature (simplified threshold, "
        "not the official IMD daily heatwave criteria).")


def fmt(value, digits=1):
    """Show missing values as '-'."""
    return "-" if value is None else f"{value:.{digits}f}"


def make_table(parent, columns, widths):
    """Create a Treeview with a vertical scrollbar inside a frame."""
    frame = ttk.Frame(parent)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col, w in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor="center")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    return frame, tree


class App:
    def __init__(self, root):
        self.root = root
        root.title("Heatwave Monitor - Indian Cities")
        root.geometry("1000x650")
        root.configure(bg=BG)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10), background=BG)
        style.configure("Title.TLabel", font=(FONT, 16, "bold"))
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"))

        self.cities = db.get_cities()
        self.years = ["All"] + [str(y) for y in db.get_years()]

        ttk.Label(root, text="Heatwave Monitor - Indian Cities",
                  style="Title.TLabel").grid(row=0, column=0, pady=10)

        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10)
        notebook.add(self.build_dashboard_tab(notebook), text="Dashboard")
        notebook.add(self.build_city_tab(notebook), text="City Data")
        notebook.add(self.build_heat_tab(notebook), text="Heat Months")
        notebook.add(self.build_summary_tab(notebook), text="Summary")
        notebook.add(self.build_charts_tab(notebook), text="Charts")

        ttk.Label(root, text="Data: popular_cities_weather.csv | Project: KJS-CES-01"
                  ).grid(row=2, column=0, pady=6)

    # ---------- Tab 1: Dashboard ----------
    def build_dashboard_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Row of small "cards" with key numbers
        o = db.get_overview()
        city, date, tmax = o["hottest"]
        cards = [
            ("Total records", str(o["total"])),
            ("Cities", str(o["cities"])),
            ("Years", str(o["years"])),
            ("Average Max Temp", f"{fmt(o['avg_tmax'])} °C"),
            ("Months >= 40 °C", str(o["months_40"])),
            ("Highest Max Temp", f"{fmt(tmax)} °C\n{city}, {date}"),
        ]
        row = ttk.Frame(tab)
        row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i, (title, value) in enumerate(cards):
            row.columnconfigure(i, weight=1)
            card = ttk.LabelFrame(row, text=title, padding=8)
            card.grid(row=0, column=i, sticky="nsew", padx=4)
            ttk.Label(card, text=value, font=(FONT, 13, "bold"),
                      justify="center").pack()

        # Three small charts for all cities
        fig = Figure(figsize=(9, 3.6), dpi=100)
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)

        years = db.get_yearly_avg_tmax()
        ax1.plot([y for y, _ in years], [t for _, t in years], marker="o")
        ax1.set_title("Avg Max Temp by Year")
        ax1.set_ylabel("°C")

        per_year = db.get_heat_months_per_year()
        ax2.bar([str(y) for y, _ in per_year], [c for _, c in per_year], color="orange")
        ax2.set_title("Months >= 40 °C by Year")

        counts = db.get_heat_level_counts()
        ax3.pie(counts.values(), labels=counts.keys(), autopct="%1.0f%%",
                textprops={"fontsize": 8})
        ax3.set_title("Heat Levels (all months)")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        canvas.draw()
        ttk.Label(tab, text=NOTE).grid(row=2, column=0, sticky="w", pady=(8, 0))
        return tab

    # ---------- Tab 2: City Data ----------
    def build_city_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(bar, text="City:").pack(side="left")
        self.city1 = ttk.Combobox(bar, values=self.cities, state="readonly", width=20)
        self.city1.pack(side="left", padx=5)
        ttk.Label(bar, text="Year:").pack(side="left", padx=(15, 0))
        self.year1 = ttk.Combobox(bar, values=self.years, state="readonly", width=8)
        self.year1.pack(side="left", padx=5)

        cols = ("Date", "Avg Temp", "Min Temp", "Max Temp", "Rainfall", "Pressure", "Heat Level")
        frame, self.tree1 = make_table(tab, cols, [100, 90, 90, 90, 90, 90, 130])
        frame.grid(row=1, column=0, sticky="nsew")
        ttk.Label(tab, text=NOTE).grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.city1.bind("<<ComboboxSelected>>", lambda e: self.refresh_city())
        self.year1.bind("<<ComboboxSelected>>", lambda e: self.refresh_city())
        self.city1.set(self.cities[0])
        self.year1.set("All")
        self.refresh_city()
        return tab

    def refresh_city(self):
        self.tree1.delete(*self.tree1.get_children())
        year = None if self.year1.get() == "All" else int(self.year1.get())
        for date, tavg, tmin, tmax, prcp, pres in db.get_city_data(self.city1.get(), year):
            self.tree1.insert("", "end", values=(
                date, fmt(tavg), fmt(tmin), fmt(tmax), fmt(prcp), fmt(pres),
                db.heat_level(tmax)))

    # ---------- Tab 3: Heat Months ----------
    def build_heat_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(bar, text="Year:").pack(side="left")
        self.year2 = ttk.Combobox(bar, values=self.years, state="readonly", width=8)
        self.year2.pack(side="left", padx=5)
        ttk.Label(bar, text="Minimum heat level:").pack(side="left", padx=(15, 0))
        levels = [name for _, name in reversed(db.HEAT_LEVELS)]  # Hot, Heatwave-prone, Severe
        self.level2 = ttk.Combobox(bar, values=levels, state="readonly", width=16)
        self.level2.pack(side="left", padx=5)

        self.count_label = ttk.Label(tab, text="")
        self.count_label.grid(row=1, column=0, sticky="w", pady=(0, 5))

        frame, self.tree2 = make_table(tab, ("City", "Date", "Max Temp", "Heat Level"),
                                       [200, 120, 100, 150])
        frame.grid(row=2, column=0, sticky="nsew")
        ttk.Label(tab, text=NOTE).grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.year2.bind("<<ComboboxSelected>>", lambda e: self.refresh_heat())
        self.level2.bind("<<ComboboxSelected>>", lambda e: self.refresh_heat())
        self.year2.set("All")
        self.level2.set(levels[0])
        self.refresh_heat()
        return tab

    def refresh_heat(self):
        self.tree2.delete(*self.tree2.get_children())
        year = None if self.year2.get() == "All" else int(self.year2.get())
        rows = db.get_heat_months(self.level2.get(), year)
        self.count_label.config(text=f"Matching records: {len(rows)}")
        for city, date, tmax in rows:
            self.tree2.insert("", "end", values=(city, date, fmt(tmax), db.heat_level(tmax)))

    # ---------- Tab 4: Summary ----------
    def build_summary_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(bar, text="City:").pack(side="left")
        self.city3 = ttk.Combobox(bar, values=self.cities, state="readonly", width=20)
        self.city3.pack(side="left", padx=5)

        # Left side: summary labels and top 5 list
        left = ttk.Frame(tab)
        left.grid(row=1, column=0, sticky="nw", padx=(0, 15))
        self.summary_label = ttk.Label(left, text="", justify="left")
        self.summary_label.pack(anchor="w")
        ttk.Label(left, text="Top 5 hottest cities (highest Max Temp):",
                  font=(FONT, 10, "bold")).pack(anchor="w", pady=(20, 4))
        top = db.get_top_hottest_cities(5)
        text = "\n".join(f"{i}. {c} - {fmt(t)} °C" for i, (c, t) in enumerate(top, 1))
        ttk.Label(left, text=text, justify="left").pack(anchor="w")

        # Right side: matplotlib chart
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=tab)
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nsew")

        self.city3.bind("<<ComboboxSelected>>", lambda e: self.refresh_summary())
        self.city3.set(self.cities[0])
        self.refresh_summary()
        return tab

    def refresh_summary(self):
        city = self.city3.get()
        s = db.get_city_summary(city)
        hottest = f"{s['hottest'][0]} ({fmt(s['hottest'][1])} °C)" if s["hottest"] else "-"
        self.summary_label.config(text=(
            f"City: {city}\n\n"
            f"Hottest month: {hottest}\n"
            f"Months with Max Temp >= 40 °C: {s['months_40']}\n"
            f"Average Max Temp: {fmt(s['avg_tmax'])} °C\n"
            f"Average Rainfall: {fmt(s['avg_prcp'])} mm"))

        # Redraw the line chart
        data = db.get_tmax_series(city)
        dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in data]
        values = [t for _, t in data]
        self.ax.clear()
        self.ax.plot(dates, values, marker="o", markersize=3)
        self.ax.axhline(40, linestyle="--", color="red", label="40 °C")
        self.ax.set_title(f"Monthly Max Temperature - {city}")
        self.ax.set_ylabel("Max Temp (°C)")
        self.ax.legend()
        self.figure.autofmt_xdate()
        self.figure.tight_layout()
        self.canvas.draw()

    # ---------- Tab 5: Charts (choose a plot type) ----------
    CHART_TYPES = [
        "Line chart - Max Temp over time",
        "Bar chart - Monthly average Max/Min Temp",
        "Bar chart - Monthly average Rainfall",
        "Histogram - Max Temp distribution",
        "Box plot - Max Temp by year",
        "Scatter plot - Max Temp vs Rainfall",
        "Pie chart - Heat level share",
        "Area chart - Temperature range (Min to Max)",
        "Comparison - Max Temp of two cities",
    ]

    def build_charts_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(bar, text="Chart type:").pack(side="left")
        self.chart_type = ttk.Combobox(bar, values=self.CHART_TYPES, state="readonly", width=42)
        self.chart_type.pack(side="left", padx=5)
        ttk.Label(bar, text="City:").pack(side="left", padx=(15, 0))
        self.city5 = ttk.Combobox(bar, values=self.cities, state="readonly", width=16)
        self.city5.pack(side="left", padx=5)
        ttk.Label(bar, text="Compare with:").pack(side="left", padx=(15, 0))
        self.city5b = ttk.Combobox(bar, values=self.cities, state="readonly", width=16)
        self.city5b.pack(side="left", padx=5)

        self.chart_fig = Figure(figsize=(8, 4.5), dpi=100)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, master=tab)
        self.chart_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        for box in (self.chart_type, self.city5, self.city5b):
            box.bind("<<ComboboxSelected>>", lambda e: self.draw_chart())
        self.chart_type.set(self.CHART_TYPES[0])
        self.city5.set(self.cities[0])
        self.city5b.set(self.cities[1])
        self.draw_chart()
        return tab

    def draw_chart(self):
        """Draw the chart chosen in the dropdown."""
        kind = self.chart_type.get()
        city = self.city5.get()
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.chart_fig.clear()
        ax = self.chart_fig.add_subplot(111)

        if kind.startswith("Line"):
            data = db.get_tmax_series(city)
            ax.plot([datetime.strptime(d, "%Y-%m-%d") for d, _ in data],
                    [t for _, t in data], marker="o", markersize=3)
            ax.axhline(40, linestyle="--", color="red", label="40 °C")
            ax.set_ylabel("Max Temp (°C)")
            ax.legend()
            self.chart_fig.autofmt_xdate()

        elif kind.startswith("Bar chart - Monthly average Max"):
            data = db.get_monthly_avg(city)
            x = range(len(data))
            ax.bar([i - 0.2 for i in x], [r[1] or 0 for r in data], width=0.4,
                   label="Avg Max", color="tomato")
            ax.bar([i + 0.2 for i in x], [r[2] or 0 for r in data], width=0.4,
                   label="Avg Min", color="steelblue")
            ax.set_xticks(list(x))
            ax.set_xticklabels([months[r[0] - 1] for r in data])
            ax.set_ylabel("°C")
            ax.legend()

        elif kind.startswith("Bar chart - Monthly average Rain"):
            data = db.get_monthly_avg(city)
            ax.bar([months[r[0] - 1] for r in data], [r[3] or 0 for r in data],
                   color="teal")
            ax.set_ylabel("Rainfall (mm)")

        elif kind.startswith("Histogram"):
            values = [r[2] for r in db.get_city_column(city, "tmax")]
            ax.hist(values, bins=12, color="orange", edgecolor="black")
            ax.axvline(40, linestyle="--", color="red", label="40 °C")
            ax.set_xlabel("Max Temp (°C)")
            ax.set_ylabel("Number of months")
            ax.legend()

        elif kind.startswith("Box"):
            rows = db.get_city_column(city, "tmax")
            years = sorted({r[1] for r in rows})
            ax.boxplot([[r[2] for r in rows if r[1] == y] for y in years])
            ax.set_xticks(range(1, len(years) + 1))
            ax.set_xticklabels([str(y) for y in years])
            ax.set_ylabel("Max Temp (°C)")

        elif kind.startswith("Scatter"):
            data = db.get_tmax_prcp(city)
            ax.scatter([t for t, _ in data], [p for _, p in data], color="purple", alpha=0.7)
            ax.set_xlabel("Max Temp (°C)")
            ax.set_ylabel("Rainfall (mm)")

        elif kind.startswith("Pie"):
            counts = {k: v for k, v in db.get_heat_level_counts(city).items() if v > 0}
            ax.pie(counts.values(), labels=counts.keys(), autopct="%1.0f%%")

        elif kind.startswith("Area"):
            tmin = db.get_city_column(city, "tmin")
            tmax = dict((d, t) for d, _, t in db.get_city_column(city, "tmax"))
            pairs = [(d, lo, tmax[d]) for d, _, lo in tmin if d in tmax]
            dates = [datetime.strptime(d, "%Y-%m-%d") for d, _, _ in pairs]
            ax.fill_between(dates, [p[1] for p in pairs], [p[2] for p in pairs],
                            color="salmon", alpha=0.5, label="Min to Max")
            ax.set_ylabel("°C")
            ax.legend()
            self.chart_fig.autofmt_xdate()

        elif kind.startswith("Comparison"):
            for c in (city, self.city5b.get()):
                data = db.get_tmax_series(c)
                ax.plot([datetime.strptime(d, "%Y-%m-%d") for d, _ in data],
                        [t for _, t in data], label=c)
            ax.axhline(40, linestyle="--", color="red")
            ax.set_ylabel("Max Temp (°C)")
            ax.legend()
            self.chart_fig.autofmt_xdate()

        title = kind.split(" - ")[1]
        ax.set_title(f"{title} - {city}" if not kind.startswith("Comparison")
                     else f"Max Temp: {city} vs {self.city5b.get()}")
        self.chart_fig.tight_layout()
        self.chart_canvas.draw()


def main():
    root = tk.Tk()
    # Make sure the CSV or database exists before starting
    if not os.path.exists(db.CSV_FILE) and not os.path.exists(db.DB_FILE):
        root.withdraw()
        messagebox.showerror("File not found",
                             "popular_cities_weather.csv was not found next to main.py.")
        return
    try:
        db.setup_database()
    except Exception as err:
        root.withdraw()
        messagebox.showerror("Database error", f"Could not load data:\n{err}")
        return
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
