"""Seed built-in AI manager preset questions.

Revision ID: 20260725_0005
Revises: 20260724_0005
Create Date: 2026-07-25
"""

from alembic import op


revision = "20260725_0005"
down_revision = "20260724_0005"
branch_labels = None
depends_on = None


BUILTIN_AGENT_ID = "00000000-0000-0000-0000-000000000001"
PRESET_QUESTIONS = (
    ("00000000-0000-0000-0000-000000000101", "产品品类多，生产资料一大堆，如何快速找到生产信息？"),
    ("00000000-0000-0000-0000-000000000102", "怎么维护知识库，才能更轻松地完成合同等文本工作？"),
    ("00000000-0000-0000-0000-000000000103", "如何搭建智能客服应用？"),
    ("00000000-0000-0000-0000-000000000104", "我创建的文档，其他同事可以看到吗？"),
    ("00000000-0000-0000-0000-000000000105", "如何一次性把现有资料放到知识库中？"),
    ("00000000-0000-0000-0000-000000000106", "支持在线编辑吗？"),
    ("00000000-0000-0000-0000-000000000107", "支持上传文件夹吗？"),
)


def upgrade() -> None:
    for display_order, (question_id, content) in enumerate(PRESET_QUESTIONS):
        op.execute(
            """INSERT INTO agent_preset_questions (id, agent_id, content, display_order, created_at)
            VALUES ('{question_id}', '{agent_id}', '{content}', {display_order}, now())
            ON CONFLICT (agent_id, display_order) DO UPDATE SET content = EXCLUDED.content""".format(
                question_id=question_id,
                agent_id=BUILTIN_AGENT_ID,
                content=content.replace("'", "''"),
                display_order=display_order,
            )
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM agent_preset_questions WHERE id IN ({})".format(
            ", ".join("'{}'".format(question_id) for question_id, _ in PRESET_QUESTIONS)
        )
    )
