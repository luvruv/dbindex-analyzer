-- ==============================================================================
-- Sample E-Commerce Database Schema and Seed Data
-- ==============================================================================
-- Purpose:
-- This script sets up a synthetic e-commerce database for testing and demonstrating
-- the DbIndex Analyzer tool.
--
-- How to load this into PostgreSQL:
-- 1. Create a database:  createdb sampledb
-- 2. Execute script:     psql -d sampledb -f sample/sample_db.sql
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Table Definitions
-- ------------------------------------------------------------------------------

-- Users Table:
-- Stores customer profiles.
-- - id: Auto-incrementing primary key (PostgreSQL automatically creates an index on primary keys).
-- - username: Lookup key (matches 'lookup_key' heuristic rule).
-- - email: Customer email (matches 'email' heuristic rule).
-- - phone: Customer contact (matches 'phone' heuristic rule).
-- - status: Account status, e.g. 'active', 'suspended' (matches 'status' heuristic rule).
-- - created_at: Account creation timestamp (matches 'date_column' heuristic rule).
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT now()
);

-- Products Table:
-- Stores catalog items for sale.
-- - id: Auto-incrementing primary key.
-- - sku: Stock Keeping Unit / item code (matches 'lookup_key' heuristic rule).
-- - name: Product title.
-- - category: Product classification (matches 'status' / category heuristic rule).
-- - price: Product cost in currency (NUMERIC preserves exact precision).
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(30),
    name VARCHAR(100),
    category VARCHAR(50),
    price NUMERIC(10,2)
);

-- Orders Table:
-- Stores customer purchasing transactions.
-- - id: Auto-incrementing primary key.
-- - user_id: Foreign key pointing to users(id).
--   IMPORTANT: PostgreSQL does NOT automatically create indexes on foreign key columns!
--   Without an index on user_id, queries like "SELECT * FROM orders WHERE user_id = 42"
--   require scanning all 200,000 orders sequentially.
-- - status: Order fulfillment state, e.g. 'paid', 'pending' (matches 'status' rule).
-- - ordered_at: Timestamp of purchase (matches 'date_column' rule).
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    status VARCHAR(20),
    ordered_at TIMESTAMP DEFAULT now()
);

-- Order Items Table:
-- Junction / line items table linking products to orders.
-- - id: Auto-incrementing primary key.
-- - order_id: Foreign key pointing to orders(id).
-- - product_id: Foreign key pointing to products(id).
-- - quantity: Number of items purchased.
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT
);

-- ------------------------------------------------------------------------------
-- 2. Synthetic Seed Data Generation
-- ------------------------------------------------------------------------------
-- Why bulk data is generated:
-- In tiny databases (e.g., 10 rows), the PostgreSQL query planner often chooses
-- sequential scans even if indexes exist because reading a single disk page is faster.
-- Generating hundreds of thousands of rows simulates realistic production conditions,
-- demonstrating the dramatic speed difference between indexed and unindexed queries.
--
-- generate_series(start, stop):
-- A built-in PostgreSQL function that generates a sequence of numbers from start to stop.
-- The string concatenation operator (||) is used to generate realistic strings.
-- The modulo operator (%) wraps numbers to match valid foreign key ID ranges.

-- Populate 100,000 synthetic users:
INSERT INTO users (username, email, phone, status)
SELECT 'user'||g, 'user'||g||'@example.com', '555'||g, 'active'
FROM generate_series(1,100000) g;

-- Populate 5,000 synthetic products across 10 categories:
INSERT INTO products (sku, name, category, price)
SELECT 'SKU'||g, 'Product '||g, 'cat'||(g%10), g%500 FROM generate_series(1,5000) g;

-- Populate 200,000 orders distributed among the 100,000 users:
INSERT INTO orders (user_id, status)
SELECT (g%100000)+1, 'paid' FROM generate_series(1,200000) g;

-- Populate 300,000 order items linking orders and products:
INSERT INTO order_items (order_id, product_id, quantity)
SELECT (g%200000)+1, (g%5000)+1, 1 FROM generate_series(1,300000) g;