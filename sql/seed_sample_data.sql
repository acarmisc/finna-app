-- sql/seed_sample_data.sql
-- Seeds sample data if not already applied (idempotent).

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM fin_projects WHERE slug = 'demo-project') THEN
        RAISE NOTICE 'Seed data already applied, skipping.';
        RETURN;
    END IF;

    INSERT INTO fin_projects (id, name, slug, owner, cost_center, budget_cap, mtd, tags, created_at, note, provider)
    VALUES
        ('p_platform', 'Platform', 'platform', 'platform-eng@acme.co', 'eng-001', 14000, 8412.22, '{"env":"prod","business_unit":"core"}'::jsonb, now() - interval '30 days', 'Core platform + shared data infra.', 'azure'),
        ('p_ml', 'ML & AI', 'ml-ai', 'ml-team@acme.co', 'ml-002', 3500, 1241.40, '{"env":"mixed","business_unit":"ai"}'::jsonb, now() - interval '20 days', 'Training, serving and LLM spend.', 'gcp'),
        ('p_analytics', 'Analytics', 'analytics', 'data@acme.co', 'data-004', 10000, 4094.41, '{"env":"prod","business_unit":"data"}'::jsonb, now() - interval '60 days', 'BI, dashboards, warehouse.', 'azure'),
        ('p_dev', 'Dev & Staging', 'dev', 'devops@acme.co', 'eng-002', 900, 208.00, '{"env":"dev","business_unit":"core"}'::jsonb, now() - interval '25 days', 'Developer sandboxes and CI.', 'gcp')
    ON CONFLICT (id) DO NOTHING;

    RAISE NOTICE 'Sample data seeded successfully.';
END $$;
