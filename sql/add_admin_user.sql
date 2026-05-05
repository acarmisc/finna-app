-- Add admin user to staging database
-- Password: admin
-- Hash generated with: bcrypt (passlib)

INSERT INTO auth_users (username, email, hashed_password, is_active, is_admin)
VALUES (
    'admin', 
    'admin@finops.local',
    '$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG',
    true, 
    true
)
ON CONFLICT (username) 
DO UPDATE SET 
    hashed_password = EXCLUDED.hashed_password,
    is_active = true,
    is_admin = true
RETURNING id, username, email, is_active, is_admin;
