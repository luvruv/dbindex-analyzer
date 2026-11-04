-- =============================================================================
-- DbIndex Analyzer - Production Database Optimization Script
-- Generated: 2026-11-04 08:10:59
-- =============================================================================

-- =============================================================================
-- PART 1: MISSING INDEXES (CREATE TO ACCELERATE READ PERFORMANCE)
-- =============================================================================

-- [CRITICAL] order_items.product_id
-- Why: Foreign key referencing 'products'; speeds up JOINs and prevents lock escalations on parent deletes
-- Expected Speedup: 10-100x
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- [CRITICAL] orders.customer_id
-- Why: Foreign key referencing 'customers'; speeds up JOINs and prevents lock escalations on parent deletes
-- Expected Speedup: 10-100x
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);

-- [CRITICAL] reviews.customer_id
-- Why: Foreign key referencing 'customers'; speeds up JOINs and prevents lock escalations on parent deletes
-- Expected Speedup: 10-100x
CREATE INDEX IF NOT EXISTS idx_reviews_customer_id ON reviews(customer_id);

-- [CRITICAL] reviews.product_id
-- Why: Foreign key referencing 'products'; speeds up JOINs and prevents lock escalations on parent deletes
-- Expected Speedup: 10-100x
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);

-- [HIGH] customers.email
-- Why: Email is often used in WHERE clauses (login, search)
-- Expected Speedup: 50-100x
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

-- [HIGH] customers.phone
-- Why: Phone numbers are often searched directly
-- Expected Speedup: 20-50x
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

-- [HIGH] products.sku
-- Why: Lookup keys are searched by exact value in APIs and queries
-- Expected Speedup: 20-50x
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);

-- [MEDIUM] customers.created_at
-- Why: Date/time columns are heavily used in range filters (BETWEEN) and ORDER BY sorting
-- Expected Speedup: 5-20x
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at);

-- [MEDIUM] orders.status
-- Why: Status/type columns are often filtered in WHERE clauses
-- Expected Speedup: 5-20x
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- [MEDIUM] orders.order_date
-- Why: Date/time columns are heavily used in range filters (BETWEEN) and ORDER BY sorting
-- Expected Speedup: 5-20x
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);

-- [MEDIUM] products.created_at
-- Why: Date/time columns are heavily used in range filters (BETWEEN) and ORDER BY sorting
-- Expected Speedup: 5-20x
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at);

-- [MEDIUM] reviews.created_at
-- Why: Date/time columns are heavily used in range filters (BETWEEN) and ORDER BY sorting
-- Expected Speedup: 5-20x
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at);


-- =============================================================================
-- PART 2: REDUNDANT & UNNECESSARY INDEXES (DROP TO SAVE STORAGE & WRITE I/O)
-- =============================================================================

-- [REDUNDANT: REDUNDANT_PK] Table: customers | Index: idx_customers_pk_redundant (id)
-- Reason: Column 'id' is already the Primary Key. Primary Keys are automatically indexed with a unique B-Tree index by the database.
-- Impact: Consumes unnecessary RAM and disk space, and slows down every INSERT and UPDATE on this table.
DROP INDEX IF EXISTS idx_customers_pk_redundant;

-- [REDUNDANT: DUPLICATE] Table: order_items | Index: idx_order_items_order (order_id)
-- Reason: Exact duplicate of index 'idx_order_items_order_dup' on (order_id). Both indexes maintain the exact same B-Tree structure.
-- Impact: Doubles write amplification on INSERT/UPDATE/DELETE operations with 0% query performance benefit.
DROP INDEX IF EXISTS idx_order_items_order;

-- [REDUNDANT: REDUNDANT_PREFIX] Table: products | Index: idx_products_category_redundant (category_id)
-- Reason: Redundant leading prefix of composite index 'idx_products_composite' on (category_id, price). The composite index satisfies any filter on 'category_id'.
-- Impact: Redundant index maintenance during writes. Safe to drop because the composite index covers queries on 'category_id'.
DROP INDEX IF EXISTS idx_products_category_redundant;

