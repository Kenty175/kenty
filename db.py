import os
import mysql.connector
from mysql.connector import Error


class AniLinkError(Exception):
    """User-friendly database or validation error."""


def get_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "anilink_db"),
            connection_timeout=5,
        )
        if conn.is_connected():
            return conn
    except Error as err:
        raise AniLinkError(f"MySQL connection failed: {err}") from err
    raise AniLinkError("Could not establish MySQL connection.")


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cooperatives (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                region VARCHAR(80) NOT NULL,
                contact_info VARCHAR(120) DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS harvest_batches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                coop_id INT NOT NULL,
                crop_name VARCHAR(100) NOT NULL,
                quantity_kg DECIMAL(10, 2) NOT NULL,
                farmgate_price DECIMAL(10, 2) NOT NULL,
                harvest_date DATE NOT NULL,
                shelf_life_days INT NOT NULL DEFAULT 5,
                status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE',
                FOREIGN KEY (coop_id) REFERENCES cooperatives(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS buyer_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                buyer_name VARCHAR(120) NOT NULL,
                hub_location VARCHAR(100) NOT NULL,
                crop_name VARCHAR(100) NOT NULL,
                demand_kg DECIMAL(10, 2) NOT NULL,
                delivery_date DATE NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_routes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_code VARCHAR(50) NOT NULL,
                cold_chain TINYINT(1) NOT NULL DEFAULT 1,
                capacity_kg DECIMAL(10, 2) NOT NULL,
                origin_region VARCHAR(80) NOT NULL,
                destination_hub VARCHAR(100) NOT NULL,
                estimated_km DECIMAL(8, 2) NOT NULL,
                est_spoilage_pct DECIMAL(5, 2) NOT NULL DEFAULT 8.0,
                surplus_alert VARCHAR(255) DEFAULT 'Normal'
            )
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def seed_sample_data():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM cooperatives")
        if cur.fetchone()[0] > 0:
            return

        cur.executemany(
            "INSERT INTO cooperatives (name, region, contact_info) VALUES (%s, %s, %s)",
            [
                ("La Trinidad Highland Growers", "Benguet", "0917-555-0101"),
                ("Manolo Fortich Veggie Co-op", "Bukidnon", "0917-555-0102"),
                ("Valencia Agro Alliance", "Bukidnon", "0917-555-0103"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO harvest_batches
                (coop_id, crop_name, quantity_kg, farmgate_price, harvest_date, shelf_life_days, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (1, "Cabbage", 2400, 22.00, "2026-11-26", 7, "AVAILABLE"),
                (1, "Carrots", 1800, 35.00, "2026-11-26", 10, "AVAILABLE"),
                (2, "Tomatoes", 2100, 28.00, "2026-11-25", 4, "AVAILABLE"),
                (3, "Bell Pepper", 950, 65.00, "2026-11-27", 5, "AVAILABLE"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO buyer_orders
                (buyer_name, hub_location, crop_name, demand_kg, delivery_date, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                ("Metro Kitchen Group", "Metro Manila", "Cabbage", 1500, "2026-11-27", "PENDING"),
                ("FreshMart Supermarkets", "Metro Manila", "Carrots", 1200, "2026-11-27", "PENDING"),
                ("Cebu Harbor Bistro", "Cebu", "Tomatoes", 900, "2026-11-26", "PENDING"),
            ],
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def fetch_all():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.id, c.name, c.region, c.contact_info,
                   COUNT(h.id) AS batch_count,
                   COALESCE(SUM(h.quantity_kg), 0) AS total_kg
            FROM cooperatives c
            LEFT JOIN harvest_batches h ON h.coop_id = c.id
            GROUP BY c.id, c.name, c.region, c.contact_info
            ORDER BY c.name, c.id
        """)
        coops = cur.fetchall()

        cur.execute("""
            SELECT h.*, c.name AS coop_name, c.region
            FROM harvest_batches h
            JOIN cooperatives c ON c.id = h.coop_id
            ORDER BY h.harvest_date, h.id DESC
        """)
        batches = cur.fetchall()

        cur.execute("SELECT * FROM buyer_orders ORDER BY delivery_date, id DESC")
        orders = cur.fetchall()

        cur.execute("SELECT * FROM dispatch_routes ORDER BY id DESC")
        routes = cur.fetchall()

        return {
            "cooperatives": coops,
            "batches": batches,
            "orders": orders,
            "routes": routes,
        }
    finally:
        cur.close()
        conn.close()


def add_cooperative(name, region, contact_info):
    if not name.strip() or not region.strip():
        raise AniLinkError("Cooperative name and region are required.")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO cooperatives (name, region, contact_info) VALUES (%s, %s, %s)",
            (name.strip(), region.strip(), contact_info.strip()),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_harvest_batch(coop_id, crop_name, quantity_kg, farmgate_price, harvest_date, shelf_life_days):
    if not crop_name.strip():
        raise AniLinkError("Crop name is required.")
    if quantity_kg <= 0 or farmgate_price <= 0:
        raise AniLinkError("Quantity and farmgate price must be greater than zero.")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO harvest_batches
                (coop_id, crop_name, quantity_kg, farmgate_price, harvest_date, shelf_life_days, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'AVAILABLE')
            """,
            (int(coop_id), crop_name.strip(), float(quantity_kg), float(farmgate_price),
             harvest_date.strip(), int(shelf_life_days)),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_buyer_order(buyer_name, hub_location, crop_name, demand_kg, delivery_date):
    if not buyer_name.strip() or not hub_location.strip() or not crop_name.strip():
        raise AniLinkError("Buyer name, hub location, and crop name are required.")
    if demand_kg <= 0:
        raise AniLinkError("Demand (kg) must be greater than zero.")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO buyer_orders
                (buyer_name, hub_location, crop_name, demand_kg, delivery_date, status)
            VALUES (%s, %s, %s, %s, %s, 'PENDING')
            """,
            (buyer_name.strip(), hub_location.strip(), crop_name.strip(), float(demand_kg), delivery_date.strip()),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def save_dispatch_route(route):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO dispatch_routes
                (vehicle_code, cold_chain, capacity_kg, origin_region, destination_hub,
                 estimated_km, est_spoilage_pct, surplus_alert)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                route["vehicle_code"],
                route["cold_chain"],
                route["capacity_kg"],
                route["origin_region"],
                route["destination_hub"],
                route["estimated_km"],
                route["est_spoilage_pct"],
                route["surplus_alert"],
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def delete_record(table, record_id):
    allowed = {"cooperatives", "harvest_batches", "buyer_orders", "dispatch_routes"}
    if table not in allowed:
        raise AniLinkError("Invalid table.")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM {table} WHERE id = %s", (int(record_id),))
        conn.commit()
    finally:
        cur.close()
        conn.close()