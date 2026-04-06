-- Sync existing subject_sources with their playbook_templates
-- Run this after updating playbook_templates to propagate changes
-- to existing subjects. Only updates fields that come from templates;
-- does NOT overwrite user_inputs (user-configured URLs).
--
-- Usage: psql cim_db -f backend/tools/sync_sources_with_templates.sql

-- Update collection_tool, collection_config, and signal_instructions
-- from the template, but preserve user_inputs
UPDATE subject_sources ss
SET
    collection_tool = pt.collection_tool,
    collection_config = pt.collection_config,
    signal_instructions = pt.signal_instructions
FROM playbook_templates pt
WHERE ss.template_id = pt.template_id
  AND ss.deleted = 0
  AND (
    ss.collection_tool != pt.collection_tool
    OR ss.collection_config::text != pt.collection_config::text
    OR ss.signal_instructions != pt.signal_instructions
  );

-- Report current state
SELECT
    gs.gsubject_name AS subject,
    ss.category_key,
    ss.collection_tool AS source_tool,
    pt.collection_tool AS template_tool,
    CASE WHEN ss.collection_tool = pt.collection_tool THEN 'ok' ELSE 'MISMATCH' END AS status
FROM subject_sources ss
JOIN playbook_templates pt ON ss.template_id = pt.template_id
JOIN group_subjects gs ON ss.gsubject_id = gs.gsubject_id
WHERE ss.deleted = 0
ORDER BY gs.gsubject_name, ss.category_key;
