

CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    user_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(15)
);

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    category VARCHAR(100),
    amount DECIMAL(10, 2),
    type ENUM('entry', 'withdraw'),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);