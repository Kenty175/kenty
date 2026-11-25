import tkinter as tk
from tkinter import messagebox, ttk
import db
import engine

BG = "#f3f7f4"
SIDEBAR_BG = "#0f2e22"
ACCENT = "#1b7a4b"
WHITE = "#ffffff"
INK = "#132a20"
MUTED = "#5c7368"
LINE = "#dce6e0"


class AniLinkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AniLink PH — AI Farm-to-Consumer Logistics")
        self.geometry("1260x780")
        self.minsize(1040, 680)
        self.configure(bg=BG)

        self.data = {"cooperatives": [], "batches": [], "orders": [], "routes": []}
        self.active_tab = "overview"

        self._build_styles()
        self._build_layout()
        self._init_system()

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8), background=WHITE, foreground=INK)
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8),
                        background=ACCENT, foreground=WHITE)
        style.map("Accent.TButton", background=[("active", "#145c38")])
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 10), background=WHITE, fieldbackground=WHITE)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#eaf1ec", foreground=INK)

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="AniLink PH", bg=SIDEBAR_BG, fg=WHITE,
                 font=("Segoe UI Bold", 18)).pack(anchor="w", padx=20, pady=(26, 2))
        tk.Label(sidebar, text="AI Cold-Chain & VRP", bg=SIDEBAR_BG, fg="#9ec7b2",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(0, 28))

        self.nav_buttons = {}
        tabs = [
            ("overview", "AI Forecast & VRP"),
            ("map", "Route Map"),
            ("cooperatives", "Cooperatives"),
            ("batches", "Harvest Batches"),
            ("orders", "Buyer Orders"),
            ("routes", "Dispatch Routes"),
        ]
        for key, label in tabs:
            btn = tk.Button(
                sidebar, text=f"  {label}", anchor="w", padx=14, pady=12,
                font=("Segoe UI Semibold", 10), relief="flat", bd=0, cursor="hand2",
                bg=SIDEBAR_BG, fg="#cde3d8", activebackground=ACCENT, activeforeground=WHITE,
                command=lambda k=key: self.switch_tab(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Main Area
        self.main = tk.Frame(self.main if hasattr(self, "main") else self, bg=BG)
        self.main.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        # Top Bar
        top = tk.Frame(self.main, bg=BG)
        top.grid(row=0, column=0, sticky="ew")
        self.page_title = tk.Label(top, text="AI Forecast & VRP", bg=BG, fg=INK, font=("Segoe UI Bold", 22))
        self.page_title.pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_data).pack(side="right")
        ttk.Button(top, text="Run AI Plan", style="Accent.TButton", command=self.run_ai_plan).pack(side="right", padx=8)

        # KPI Cards
        kpi_row = tk.Frame(self.main, bg=BG)
        kpi_row.grid(row=1, column=0, sticky="ew", pady=16)
        self.kpi_vars = {}
        kpis = [
            ("coops", "CO-OPS"),
            ("supply_kg", "AVAILABLE HARVEST (KG)"),
            ("demand_kg", "BUYER DEMAND (KG)"),
            ("routes", "DISPATCH ROUTES"),
        ]
        for idx, (key, title) in enumerate(kpis):
            kpi_row.grid_columnconfigure(idx, weight=1, uniform="kpi")
            card = tk.Frame(kpi_row, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 6, 0 if idx == 3 else 6))
            tk.Label(card, text=title, bg=WHITE, fg=MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=14, pady=(10, 2))
            var = tk.StringVar(value="0")
            self.kpi_vars[key] = var
            tk.Label(card, textvariable=var, bg=WHITE, fg=ACCENT if idx == 0 else INK,
                     font=("Segoe UI Bold", 18)).pack(anchor="w", padx=14, pady=(0, 10))

        # Dynamic Content Container
        self.content = tk.Frame(self.main, bg=BG)
        self.content.grid(row=2, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.main, textvariable=self.status_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").grid(row=3, column=0, sticky="ew", pady=(10, 0))

    def _init_system(self):
        try:
            db.init_db()
            db.seed_sample_data()
            self.refresh_data()
        except db.AniLinkError as err:
            self.status_var.set(str(err))
            messagebox.showwarning("Database Setup", f"{err}\n\nMake sure MySQL is running and 'anilink_db' exists.")

    def refresh_data(self):
        try:
            self.data = db.fetch_all()
            total_supply = sum(float(b["quantity_kg"]) for b in self.data["batches"] if b["status"] == "AVAILABLE")
            total_demand = sum(float(o["demand_kg"]) for o in self.data["orders"] if o["status"] == "PENDING")
            self.kpi_vars["coops"].set(str(len(self.data["cooperatives"])))
            self.kpi_vars["supply_kg"].set(f"{total_supply:,.0f}")
            self.kpi_vars["demand_kg"].set(f"{total_demand:,.0f}")
            self.kpi_vars["routes"].set(str(len(self.data["routes"])))
            self.status_var.set("Connected to MySQL · Records loaded.")
            self.switch_tab(self.active_tab)
        except db.AniLinkError as err:
            self.status_var.set(str(err))

    def switch_tab(self, tab_key):
        self.active_tab = tab_key
        titles = {
            "overview": "AI Demand Forecast, VRP & Surplus Alerts",
            "map": "Live Origin-to-Destination Route Map",
            "cooperatives": "Partner Cooperatives",
            "batches": "Harvest Batches",
            "orders": "Buyer Orders",
            "routes": "Cold-Chain Dispatch Routes",
        }
        self.page_title.config(text=titles[tab_key])
        for k, btn in self.nav_buttons.items():
            btn.config(bg=ACCENT if k == tab_key else SIDEBAR_BG, fg=WHITE if k == tab_key else "#cde3d8")

        for w in self.content.winfo_children():
            w.destroy()

        if tab_key == "overview":
            self._render_overview()
        elif tab_key == "map":
            self._render_map()
        elif tab_key == "cooperatives":
            self._render_cooperatives()
        elif tab_key == "batches":
            self._render_batches()
        elif tab_key == "orders":
            self._render_orders()
        elif tab_key == "routes":
            self._render_routes()

    def _render_overview(self):
        plan = engine.build_ai_plan(self.data["batches"], self.data["orders"], cold_chain=True)

        wrapper = tk.Frame(self.content, bg=BG)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        alert_box = tk.Frame(wrapper, bg=WHITE, highlightbackground=LINE, highlightthickness=1, padx=14, pady=10)
        alert_box.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(alert_box, text="SURPLUS & CLUSTER ALERTS", bg=WHITE, fg=ACCENT,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w")
        if plan["alerts"]:
            for msg in plan["alerts"]:
                tk.Label(alert_box, text=f"• {msg}", bg=WHITE, fg=INK, font=("Segoe UI", 10)).pack(anchor="w", pady=2)
        else:
            tk.Label(alert_box, text="• No critical surplus or shortage alerts right now.", bg=WHITE, fg=MUTED).pack(anchor="w")

        cols = ("crop", "supply_kg", "demand_kg", "forecast_7d_kg", "surplus_or_gap_kg", "status_note")
        tree = self._make_table(wrapper, cols, ["Crop", "Supply (kg)", "Demand (kg)", "7-Day Forecast (kg)", "Surplus / Gap", "AI Recommendation"])
        tree.grid(row=1, column=0, sticky="nsew")
        for f in plan["forecasts"]:
            tree.insert("", "end", values=[f[c] for c in cols])

    def _render_map(self):
        try:
            import tkintermapview
        except ImportError:
            tk.Label(
                self.content,
                text="Install tkintermapview (`pip install tkintermapview`) to view the interactive map.",
                bg=WHITE, fg=MUTED, font=("Segoe UI", 11)
            ).grid(row=0, column=0, sticky="nsew")
            return

        wrapper = tk.Frame(self.content, bg=BG)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        controls = tk.Frame(wrapper, bg=WHITE, highlightbackground=LINE, highlightthickness=1, padx=12, pady=10)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        places = list(engine.HUB_COORDS.keys())
        origin_cb = ttk.Combobox(controls, values=places, width=16)
        origin_cb.set("Benguet")
        dest_cb = ttk.Combobox(controls, values=places, width=16)
        dest_cb.set("Metro Manila")

        route_labels = {
            f"#{r['id']} {r['vehicle_code']}: {r['origin_region']} -> {r['destination_hub']}": r
            for r in self.data["routes"]
        }
        route_cb = ttk.Combobox(controls, values=list(route_labels.keys()), state="readonly", width=32)
        if route_labels:
            route_cb.set(next(iter(route_labels)))

        tk.Label(controls, text="Origin:", bg=WHITE).pack(side="left")
        origin_cb.pack(side="left", padx=(4, 10))
        tk.Label(controls, text="Destination:", bg=WHITE).pack(side="left")
        dest_cb.pack(side="left", padx=(4, 10))

        map_widget = tkintermapview.TkinterMapView(wrapper, corner_radius=8)
        map_widget.grid(row=1, column=0, sticky="nsew")

        info_var = tk.StringVar(value="Select a route or origin/destination and click Track Route.")
        tk.Label(wrapper, textvariable=info_var, bg=BG, fg=INK, font=("Segoe UI Semibold", 10), anchor="w").grid(
            row=2, column=0, sticky="ew", pady=(8, 0)
        )

        def draw_track(origin, dest, label_prefix="Custom"):
            map_widget.delete_all_marker()
            map_widget.delete_all_path()
            o_coords, d_coords, path = engine.get_route_path(origin, dest)
            dist = engine.estimate_distance_km(origin, dest)
            map_widget.set_marker(o_coords[0], o_coords[1], text=f"Origin: {origin}")
            map_widget.set_marker(d_coords[0], d_coords[1], text=f"Destination: {dest}")
            map_widget.set_path(path, color="#1b7a4b", width=4)
            mid_lat = (o_coords[0] + d_coords[0]) / 2
            mid_lon = (o_coords[1] + d_coords[1]) / 2
            map_widget.set_position(mid_lat, mid_lon)
            map_widget.set_zoom(6)
            info_var.set(f"{label_prefix} · {origin} → {dest} · Est. Distance: {dist:.0f} km")

        def on_route_selected(_=None):
            r = route_labels.get(route_cb.get())
            if r:
                origin_cb.set(r["origin_region"])
                dest_cb.set(r["destination_hub"])
                draw_track(r["origin_region"], r["destination_hub"], f"Vehicle {r['vehicle_code']}")

        route_cb.bind("<<ComboboxSelected>>", on_route_selected)
        ttk.Button(
            controls, text="Track Route", style="Accent.TButton",
            command=lambda: draw_track(origin_cb.get(), dest_cb.get())
        ).pack(side="right")

        if route_labels:
            tk.Label(controls, text="Saved Route:", bg=WHITE).pack(side="left", padx=(6, 0))
            route_cb.pack(side="left", padx=(4, 8))
            on_route_selected()
        else:
            draw_track(origin_cb.get(), dest_cb.get())

    def _render_cooperatives(self):
        top_form = tk.Frame(self.content, bg=WHITE, highlightbackground=LINE, highlightthickness=1, padx=12, pady=10)
        top_form.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        name_e = ttk.Entry(top_form, width=26)
        region_e = ttk.Combobox(top_form, values=list(engine.HUB_COORDS.keys()), width=16)
        contact_e = ttk.Entry(top_form, width=20)
        region_e.set("Benguet")

        tk.Label(top_form, text="Co-op Name:", bg=WHITE).pack(side="left")
        name_e.pack(side="left", padx=(4, 10))
        tk.Label(top_form, text="Region:", bg=WHITE).pack(side="left")
        region_e.pack(side="left", padx=(4, 10))
        tk.Label(top_form, text="Contact:", bg=WHITE).pack(side="left")
        contact_e.pack(side="left", padx=(4, 10))

        def on_add():
            try:
                db.add_cooperative(name_e.get(), region_e.get(), contact_e.get())
                self.refresh_data()
            except db.AniLinkError as err:
                messagebox.showerror("Error", str(err))

        ttk.Button(top_form, text="+ Add Co-op", style="Accent.TButton", command=on_add).pack(side="right")

        cols = ("id", "name", "region", "contact_info", "batch_count", "total_kg")
        tree = self._make_table(self.content, cols, ["ID", "Name", "Region", "Contact", "Batches", "Total kg"])
        tree.grid(row=1, column=0, sticky="nsew")
        for r in self.data["cooperatives"]:
            tree.insert("", "end", iid=str(r["id"]), values=[r[c] for c in cols])
        self._add_delete_bar(tree, "cooperatives")

    def _render_batches(self):
        form = tk.Frame(self.content, bg=WHITE, highlightbackground=LINE, highlightthickness=1, padx=12, pady=10)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        coop_map = {f"{c['name']} (#{c['id']})": c["id"] for c in self.data["cooperatives"]}
        coop_cb = ttk.Combobox(form, values=list(coop_map.keys()), state="readonly", width=24)
        if coop_map:
            coop_cb.set(next(iter(coop_map)))

        crop_e = ttk.Entry(form, width=14)
        qty_e = ttk.Entry(form, width=10)
        price_e = ttk.Entry(form, width=10)
        date_e = ttk.Entry(form, width=12)
        date_e.insert(0, "2026-11-26")

        for lbl, w in [("Co-op:", coop_cb), ("Crop:", crop_e), ("Kg:", qty_e), ("₱/kg:", price_e), ("Date:", date_e)]:
            tk.Label(form, text=lbl, bg=WHITE).pack(side="left")
            w.pack(side="left", padx=(3, 8))

        def on_add():
            try:
                if coop_cb.get() not in coop_map:
                    raise db.AniLinkError("Create a cooperative first.")
                db.add_harvest_batch(
                    coop_map[coop_cb.get()], crop_e.get(),
                    float(qty_e.get() or 0), float(price_e.get() or 0),
                    date_e.get(), 5,
                )
                self.refresh_data()
            except (ValueError, db.AniLinkError) as err:
                messagebox.showerror("Error", str(err))

        ttk.Button(form, text="+ Add Batch", style="Accent.TButton", command=on_add).pack(side="right")

        cols = ("id", "coop_name", "region", "crop_name", "quantity_kg", "farmgate_price", "harvest_date", "status")
        tree = self._make_table(self.content, cols, ["ID", "Cooperative", "Region", "Crop", "Kg", "₱/kg", "Harvest Date", "Status"])
        tree.grid(row=1, column=0, sticky="nsew")
        for r in self.data["batches"]:
            tree.insert("", "end", iid=str(r["id"]), values=[r[c] for c in cols])
        self._add_delete_bar(tree, "harvest_batches")

    def _render_orders(self):
        form = tk.Frame(self.content, bg=WHITE, highlightbackground=LINE, highlightthickness=1, padx=12, pady=10)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        buyer_e = ttk.Entry(form, width=18)
        hub_cb = ttk.Combobox(form, values=list(engine.HUB_COORDS.keys()), width=14)
        hub_cb.set("Metro Manila")
        crop_e = ttk.Entry(form, width=14)
        kg_e = ttk.Entry(form, width=10)
        date_e = ttk.Entry(form, width=12)
        date_e.insert(0, "2026-11-27")

        for lbl, w in [("Buyer:", buyer_e), ("Hub:", hub_cb), ("Crop:", crop_e), ("Demand kg:", kg_e), ("Delivery:", date_e)]:
            tk.Label(form, text=lbl, bg=WHITE).pack(side="left")
            w.pack(side="left", padx=(3, 8))

        def on_add():
            try:
                db.add_buyer_order(buyer_e.get(), hub_cb.get(), crop_e.get(), float(kg_e.get() or 0), date_e.get())
                self.refresh_data()
            except (ValueError, db.AniLinkError) as err:
                messagebox.showerror("Error", str(err))

        ttk.Button(form, text="+ Add Order", style="Accent.TButton", command=on_add).pack(side="right")

        cols = ("id", "buyer_name", "hub_location", "crop_name", "demand_kg", "delivery_date", "status")
        tree = self._make_table(self.content, cols, ["ID", "Buyer", "Hub", "Crop", "Demand (kg)", "Delivery Date", "Status"])
        tree.grid(row=1, column=0, sticky="nsew")
        for r in self.data["orders"]:
            tree.insert("", "end", iid=str(r["id"]), values=[r[c] for c in cols])
        self._add_delete_bar(tree, "buyer_orders")

    def _render_routes(self):
        cols = ("id", "vehicle_code", "cold_chain", "capacity_kg", "origin_region", "destination_hub", "estimated_km", "est_spoilage_pct", "surplus_alert")
        tree = self._make_table(self.content, cols, ["ID", "Vehicle", "Cold Chain", "Load (kg)", "Origin", "Destination", "km", "Spoilage %", "Alert / Note"])
        tree.grid(row=0, column=0, sticky="nsew")
        for r in self.data["routes"]:
            row_vals = [
                r["id"], r["vehicle_code"], "Yes" if r["cold_chain"] else "No",
                r["capacity_kg"], r["origin_region"], r["destination_hub"],
                r["estimated_km"], r["est_spoilage_pct"], r["surplus_alert"],
            ]
            tree.insert("", "end", iid=str(r["id"]), values=row_vals)
        self._add_delete_bar(tree, "dispatch_routes")

    def _make_table(self, parent, cols, headings):
        tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
        for c, h in zip(cols, headings):
            tree.heading(c, text=h, anchor="w")
            tree.column(c, width=120, anchor="w")
        return tree

    def _add_delete_bar(self, tree, table_name):
        bar = tk.Frame(self.content, bg=BG)
        bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        def on_del():
            sel = tree.selection()
            if not sel:
                return
            if messagebox.askyesno("Delete", "Delete selected record?"):
                try:
                    db.delete_record(table_name, sel[0])
                    self.refresh_data()
                except db.AniLinkError as err:
                    messagebox.showerror("Error", str(err))

        ttk.Button(bar, text="Delete Selected", command=on_del).pack(side="right")

    def run_ai_plan(self):
        try:
            plan = engine.build_ai_plan(self.data["batches"], self.data["orders"], cold_chain=True)
            for route in plan["proposed_routes"]:
                db.save_dispatch_route(route)
            self.refresh_data()
            self.switch_tab("map")
            messagebox.showinfo(
                "AI Plan Generated",
                f"Forecasted {len(plan['forecasts'])} crops, generated {len(plan['proposed_routes'])} cold-chain routes, "
                f"and logged {len(plan['alerts'])} surplus/shortage alerts.",
            )
        except db.AniLinkError as err:
            messagebox.showerror("Error", str(err))


if __name__ == "__main__":
    AniLinkApp().mainloop()