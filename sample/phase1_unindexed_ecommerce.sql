-- =============================================================================
-- Phase 1: Unindexed E-Commerce Database Schema & Data
-- =============================================================================
-- Use this file to set up a clean test database that demonstrates the need for indexing.
-- Contains:
--  - 6 relational tables with realistic relationships
--  - Unindexed Foreign Keys (causes full table scans on JOINs)
--  - Unindexed search columns (email, phone, SKU, order_date)
--  - Intentional duplicate and redundant indexes
--
-- How to load:
--   PostgreSQL: psql -U postgres -d postgres -c "CREATE DATABASE ecommerce_test;"
--               psql -U postgres -d ecommerce_test -f sample/phase1_unindexed_ecommerce.sql
--   SQLite:     sqlite3 ecommerce_test.db < sample/phase1_unindexed_ecommerce.sql
-- =============================================================================

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(25),
    city VARCHAR(50),
    country VARCHAR(50) DEFAULT 'USA',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE
);

-- 3. Products Table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(30) NOT NULL,
    name VARCHAR(150) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Orders Table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_number VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(30) DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Order Items Table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- 6. Reviews Table (Unindexed FK to customers & products)
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INTENTIONAL ARCHITECTURAL FLAWS FOR THE ANALYZER TO DETECT:
-- =============================================================================

-- Flaw 1: Redundant prefix index on products(category_id)
-- idx_products_composite already covers category_id as its leading column!
CREATE INDEX idx_products_composite ON products(category_id, price);
CREATE INDEX idx_products_category_redundant ON products(category_id);

-- Flaw 2: Duplicate identical indexes on order_items(order_id)
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_order_dup ON order_items(order_id);

-- Flaw 3: Redundant manual index on Primary Key customers(id)
CREATE INDEX idx_customers_pk_redundant ON customers(id);

-- =============================================================================
-- SEED DATA (Realistic volume to demonstrate query benchmarks)
-- =============================================================================

INSERT INTO categories (name, slug) VALUES
('Smartphones', 'smartphones'),
('Laptops', 'laptops'),
('Audio', 'audio'),
('Wearables', 'wearables');

INSERT INTO customers (username, email, phone, city, country) VALUES
('john_doe', 'john.doe@example.com', '+1-555-0101', 'New York', 'USA'),
('jane_smith', 'jane.smith@techcorp.io', '+1-555-0102', 'San Francisco', 'USA'),
('alex_m', 'alex.m@datascience.org', '+1-555-0103', 'Austin', 'USA'),
('sam_wilson', 'sam.wilson@cloudops.com', '+1-555-0104', 'Chicago', 'USA'),
('emily_rose', 'emily.rose@designstudio.co', '+1-555-0105', 'Seattle', 'USA');

INSERT INTO products (category_id, sku, name, price) VALUES
(1, 'SKU-PH-01', 'ProPhone Ultra 256GB', 1099.00),
(1, 'SKU-PH-02', 'ProPhone Mini 128GB', 799.00),
(2, 'SKU-LP-01', 'Developer Workstation 16', 2199.00),
(2, 'SKU-LP-02', 'UltraBook Air 13', 1299.00),
(3, 'SKU-AU-01', 'Noise-Cancelling Headphones', 349.00),
(4, 'SKU-WR-01', 'Fitness Smartwatch Pro', 249.00);

INSERT INTO orders (customer_id, order_number, status, total_amount) VALUES
(1, 'ORD-2026-001', 'delivered', 1448.00),
(2, 'ORD-2026-002', 'processing', 2199.00),
(3, 'ORD-2026-003', 'shipped', 799.00),
(1, 'ORD-2026-004', 'delivered', 349.00),
(4, 'ORD-2026-005', 'cancelled', 249.00);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 1099.00),
(1, 5, 1, 349.00),
(2, 3, 1, 2199.00),
(3, 2, 1, 799.00),
(4, 5, 1, 349.00),
(5, 6, 1, 249.00);

INSERT INTO reviews (customer_id, product_id, rating, comment) VALUES
(1, 1, 5, 'Exceptional battery life and display quality.'),
(2, 3, 4, 'Very fast compilation times, highly recommended.'),
(3, 2, 5, 'Lightweight and powerful.'),
(1, 5, 5, 'Best noise cancelling on the market.');

