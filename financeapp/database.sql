-- FinanceOS Database Schema
-- Run this in phpMyAdmin or MySQL CLI

CREATE DATABASE IF NOT EXISTS financeos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE financeos;

-- ─── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone         VARCHAR(20),
    avatar        VARCHAR(255) DEFAULT NULL,
    currency      VARCHAR(10)  DEFAULT 'INR',
    theme         VARCHAR(10)  DEFAULT 'dark',
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ─── Transactions ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    type        ENUM('income','expense') NOT NULL,
    category    VARCHAR(50)  NOT NULL DEFAULT 'other',
    amount      DECIMAL(12,2) NOT NULL,
    note        TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_type (user_id, type),
    INDEX idx_user_date (user_id, created_at)
);

-- ─── Budgets ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS budgets (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    category     VARCHAR(50) NOT NULL,
    limit_amount DECIMAL(12,2) NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_user_cat (user_id, category)
);

-- ─── Goals ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS goals (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    name          VARCHAR(150) NOT NULL,
    target_amount DECIMAL(12,2) NOT NULL,
    saved_amount  DECIMAL(12,2) DEFAULT 0.00,
    deadline      DATE DEFAULT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ─── Sample Data (optional) ───────────────────────────────────────────────────
-- Password: demo123  (hashed below)
INSERT IGNORE INTO users (name, email, password_hash, phone, currency) VALUES
('Demo User', 'demo@financeos.com',
 'pbkdf2:sha256:600000$example$hashedpassword',  -- replace with real hash
 '9876543210', 'INR');
