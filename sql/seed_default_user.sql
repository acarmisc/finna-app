-- sql/seed_default_user.sql
INSERT INTO users (username, password_hash, email, is_active, is_superuser)
VALUES ('admin', crypt('admin_password', gen_salt('bf')), 'admin@example.com', true, true)
ON CONFLICT (username) DO NOTHING;
