"""replace gsubject_type_enum with subject_types table

Revision ID: 7d106a331687
Revises: 572b732de5e6
Create Date: 2026-04-02 19:07:16.083363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d106a331687'
down_revision: Union[str, Sequence[str], None] = '572b732de5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace gsubject_type_enum with subject_types table."""

    # 1. Create subject_types table
    op.create_table(
        'subject_types',
        sa.Column('subj_type_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subj_type_name', sa.VARCHAR(length=64), nullable=False),
        sa.Column('subj_type_desc', sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column('subj_type_enabled', sa.Boolean(), server_default=sa.text("'TRUE'"), nullable=False),
        sa.PrimaryKeyConstraint('subj_type_id'),
        sa.UniqueConstraint('subj_type_name'),
    )

    # 2. Seed the 4 existing types
    op.execute("""
        INSERT INTO subject_types (subj_type_id, subj_type_name, subj_type_desc, subj_type_enabled)
        VALUES
            (1, 'company', 'Company subjects', true),
            (2, 'product', 'Product subjects', true),
            (3, 'service', 'Service subjects', true),
            (4, 'topic', 'Topic subjects', true);
        SELECT setval('subject_types_subj_type_id_seq', 4);
    """)

    # 3. Add new FK columns (nullable initially)
    op.add_column('group_subjects', sa.Column('gsubject_type_id', sa.Integer(), nullable=True))
    op.add_column('playbook_templates', sa.Column('subject_type_id', sa.Integer(), nullable=True))

    # 4. Populate from enum values
    op.execute("""
        UPDATE group_subjects SET gsubject_type_id = CASE gsubject_type::text
            WHEN 'company' THEN 1
            WHEN 'product' THEN 2
            WHEN 'service' THEN 3
            WHEN 'topic' THEN 4
        END;
    """)
    op.execute("""
        UPDATE playbook_templates SET subject_type_id = CASE subject_type::text
            WHEN 'company' THEN 1
            WHEN 'product' THEN 2
            WHEN 'service' THEN 3
            WHEN 'topic' THEN 4
        END;
    """)

    # 5. Drop old unique constraint on playbook_templates
    op.drop_constraint('uq_playbook_subject_type_category', 'playbook_templates', type_='unique')

    # 6. Drop old enum columns
    op.drop_column('group_subjects', 'gsubject_type')
    op.drop_column('playbook_templates', 'subject_type')

    # 7. Make new columns NOT NULL
    op.alter_column('group_subjects', 'gsubject_type_id', nullable=False)
    op.alter_column('playbook_templates', 'subject_type_id', nullable=False)

    # 8. Add FK constraints
    op.create_foreign_key(
        'fk_group_subjects_subj_type_id', 'group_subjects',
        'subject_types', ['gsubject_type_id'], ['subj_type_id'],
    )
    op.create_foreign_key(
        'fk_playbook_templates_subj_type_id', 'playbook_templates',
        'subject_types', ['subject_type_id'], ['subj_type_id'],
    )

    # 9. Add new unique constraint
    op.create_unique_constraint(
        'uq_playbook_subject_type_category', 'playbook_templates',
        ['subject_type_id', 'category_key'],
    )

    # 10. Add index on group_subjects.gsubject_type_id
    op.create_index('ix_group_subjects_type_id', 'group_subjects', ['gsubject_type_id'])

    # 11. Drop the enum type
    op.execute("DROP TYPE IF EXISTS gsubject_type_enum")


def downgrade() -> None:
    """Reverse: recreate enum, restore columns, drop subject_types table."""

    # Recreate enum
    op.execute("CREATE TYPE gsubject_type_enum AS ENUM ('company', 'product', 'service', 'topic')")

    # Add back enum columns
    op.add_column('group_subjects', sa.Column('gsubject_type', sa.Enum('company', 'product', 'service', 'topic', name='gsubject_type_enum'), nullable=True))
    op.add_column('playbook_templates', sa.Column('subject_type', sa.Enum('company', 'product', 'service', 'topic', name='gsubject_type_enum'), nullable=True))

    # Populate from FK
    op.execute("""
        UPDATE group_subjects gs SET gsubject_type = st.subj_type_name::gsubject_type_enum
        FROM subject_types st WHERE gs.gsubject_type_id = st.subj_type_id;
    """)
    op.execute("""
        UPDATE playbook_templates pt SET subject_type = st.subj_type_name::gsubject_type_enum
        FROM subject_types st WHERE pt.subject_type_id = st.subj_type_id;
    """)

    # Make NOT NULL
    op.alter_column('group_subjects', 'gsubject_type', nullable=False)
    op.alter_column('playbook_templates', 'subject_type', nullable=False)

    # Drop new constraints and columns
    op.drop_index('ix_group_subjects_type_id', 'group_subjects')
    op.drop_constraint('uq_playbook_subject_type_category', 'playbook_templates', type_='unique')
    op.drop_constraint('fk_playbook_templates_subj_type_id', 'playbook_templates', type_='foreignkey')
    op.drop_constraint('fk_group_subjects_subj_type_id', 'group_subjects', type_='foreignkey')
    op.drop_column('playbook_templates', 'subject_type_id')
    op.drop_column('group_subjects', 'gsubject_type_id')

    # Restore old unique constraint
    op.create_unique_constraint('uq_playbook_subject_type_category', 'playbook_templates', ['subject_type', 'category_key'])

    # Drop subject_types table
    op.drop_table('subject_types')
