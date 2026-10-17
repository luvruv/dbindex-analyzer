CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT now()
);
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(30),
    name VARCHAR(100),
    category VARCHAR(50),
    price NUMERIC(10,2)
);
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    status VARCHAR(20),
    ordered_at TIMESTAMP DEFAULT now()
);
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT
);

INSERT INTO users (username, email, phone, status)
SELECT 'user'||g, 'user'||g||'@example.com', '555'||g, 'active'
FROM generate_series(1,100000) g;
INSERT INTO products (sku, name, category, price)
SELECT 'SKU'||g, 'Product '||g, 'cat'||(g%10), g%500 FROM generate_series(1,5000) g;
INSERT INTO orders (user_id, status)
SELECT (g%100000)+1, 'paid' FROM generate_series(1,200000) g;
INSERT INTO order_items (order_id, product_id, quantity)
SELECT (g%200000)+1, (g%5000)+1, 1 FROM generate_series(1,300000) g;