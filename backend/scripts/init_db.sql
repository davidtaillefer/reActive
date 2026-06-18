-- init_db.sql
-- Creates the database and a user (if necessary). The MariaDB image will execute
-- this script on first initialization when mounted into /docker-entrypoint-initdb.d/

CREATE DATABASE IF NOT EXISTS `exercise` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- You can add CREATE TABLE statements here or import a dump.
-- Example table (adjust columns to match your real schema):
-- CREATE TABLE IF NOT EXISTS `activities` (
--   `id` INT AUTO_INCREMENT PRIMARY KEY,
--   `date` DATE,
--   `duration` INT,
--   `sport` INT
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Grant privileges (only if you want the container to create the user)
-- Note: In production, prefer creating users separately and using secrets.
-- CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
-- GRANT ALL PRIVILEGES ON `exercise`.* TO '${DB_USER}'@'%';
-- FLUSH PRIVILEGES;
