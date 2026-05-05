-- sql/seed_default_user.sql
INSERT INTO auth_users (username, email, hashed_password, is_active, is_admin)
VALUES ('admin', 'admin@example.com', crypt('admin_password', '$2a$08$UYoRP.qb0Lx5AlFzlY0dnO'), true, true)
ON CONFLICT (username) DO NOTHING;
