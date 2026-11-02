"""Database schema generator module for DbIndex Analyzer.

Generates realistic database schemas and test datasets (in SQLite or as a PostgreSQL SQL dump).
Designed for live demos, academic presentations, and immediate local testing without external servers.

Creates intentional architectural patterns:
1. Well-indexed primary keys and unique constraints.
2. Missing indexes on foreign keys (demonstrates critical join bottleneck).
3. Missing indexes on high-frequency search columns (email, phone, status, timestamps).
4. Intentional duplicate indexes (demonstrates write-overhead and storage waste detection).
5. Intentional redundant prefix indexes (demonstrates composite index subsumption).
6. Intentional redundant index on a primary key (demonstrates engine-level waste detection).
"""

import os
import sqlite3


SAMPLE_SCHEMA_SQL = """
-- 1. Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE
);

-- 3. Products Table
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(30) NOT NULL,
    title VARCHAR(150) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Orders Table
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    order_number VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(30) DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Order Items Table
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- 6. Audit Logs Table (Table intentionally without a Primary Key to test schema health warning)
CREATE TABLE audit_logs (
    event_name VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    details TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INTENTIONAL INDEXES (Healthy, Redundant, and Duplicates for Demonstration)
-- =============================================================================

-- Healthy Composite Index on products (category_id, price)
CREATE INDEX idx_products_cat_price ON products(category_id, price);

-- Intentional Redundant Prefix Index: category_id is already covered as leading col in idx_products_cat_price!
CREATE INDEX idx_products_category_redundant ON products(category_id);

-- Intentional Redundant Index on Primary Key: products(id) is already the PK!
CREATE INDEX idx_products_id_redundant ON products(id);

-- Intentional Duplicate Index on order_items(order_id)
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_order_duplicate ON order_items(order_id);

-- Healthy Index on order_items(product_id)
CREATE INDEX idx_order_items_product ON order_items(product_id);
"""

SAMPLE_DATA_SQL = """
INSERT INTO users (id, username, email, phone, status) VALUES 
(1, 'alice', 'alice@techcorp.com', '+1-555-0101', 'active'),
(2, 'bob', 'bob@datascience.io', '+1-555-0102', 'active'),
(3, 'carol', 'carol@design.co', '+1-555-0103', 'suspended');

INSERT INTO categories (id, name, slug) VALUES 
(1, 'Electronics', 'electronics'),
(2, 'Computers', 'computers'),
(3, 'Accessories', 'accessories');

INSERT INTO products (id, category_id, sku, title, price) VALUES 
(1, 1, 'SKU-PHONE-12', 'Smartphone 12 Pro', 999.00),
(2, 2, 'SKU-LAPTOP-15', 'Developer Workstation 15', 1899.00),
(3, 3, 'SKU-MOUSE-01', 'Wireless Ergonomic Mouse', 49.99);

INSERT INTO orders (id, user_id, order_number, status, total_amount) VALUES 
(1, 1, 'ORD-2026-0001', 'delivered', 1048.99),
(2, 2, 'ORD-2026-0002', 'processing', 1899.00);

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES 
(1, 1, 1, 1, 999.00),
(2, 1, 3, 1, 49.99),
(3, 2, 2, 1, 1899.00);
"""


def generate_demo_database(output_path: str = "demo_database.db") -> str:
    """Generate a fully populated SQLite demo database with intentional missing and redundant indexes.

    Parameters:
    -----------
    output_path : str
        Target file path for the .db database.

    Returns:
    --------
    str
        Absolute path to the created SQLite database.
    """
    if os.path.exists(output_path):
        os.remove(output_path)

    conn = sqlite3.connect(output_path)
    try:
        cur = conn.cursor()
        cur.executescript(SAMPLE_SCHEMA_SQL)
        cur.executescript(SAMPLE_DATA_SQL)
        conn.commit()
    finally:
        conn.close()

    return os.path.abspath(output_path)

