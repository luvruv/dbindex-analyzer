-- =============================================================================
-- Phase 2: Query Performance Benchmark & Verification Queries
-- =============================================================================
-- Run these queries BEFORE and AFTER applying recommendations.sql.
-- Notice how the query execution plan switches from "Seq Scan" (slow table scan)
-- to "Index Scan" (O(log N) instant B-Tree traversal).
--
-- How to run in terminal:
--   psql -U postgres -d ecommerce_test -f sample/phase2_benchmark_queries.sql
-- =============================================================================

-- Benchmark Query 1: Join Orders with Customers on foreign key
-- BEFORE: Sequential Scan on orders and hash join
-- AFTER:  Index Scan on idx_orders_customer_id
EXPLAIN ANALYZE
SELECT 
    c.username,
    c.email,
    o.order_number,
    o.total_amount,
    o.status
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status = 'delivered';

-- Benchmark Query 2: Direct lookup by customer email (Login / Auth check)
-- BEFORE: Seq Scan filtering all customer rows
-- AFTER:  Index Scan using idx_customers_email
EXPLAIN ANALYZE
SELECT id, username, city 
FROM customers 
WHERE email = 'jane.smith@techcorp.io';

-- Benchmark Query 3: Range query on order_date (Dashboard / Reporting filter)
-- BEFORE: Full table scan reading every order
-- AFTER:  Index Range Scan using idx_orders_order_date
EXPLAIN ANALYZE
SELECT order_number, total_amount, status
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY order_date DESC;

-- Benchmark Query 4: Search product by SKU
-- BEFORE: Seq scan through products table
-- AFTER:  Index Scan using idx_products_sku
EXPLAIN ANALYZE
SELECT id, name, price 
FROM products 
WHERE sku = 'SKU-LP-01';

-- Benchmark Query 5: Join Reviews to Products and Customers
-- BEFORE: Sequential Scan on reviews
-- AFTER:  Index Scan using idx_reviews_product_id and idx_reviews_customer_id
EXPLAIN ANALYZE
SELECT 
    p.name AS product_name,
    c.username,
    r.rating,
    r.comment
FROM reviews r
JOIN products p ON r.product_id = p.id
JOIN customers c ON r.customer_id = c.id
WHERE r.rating >= 4;

