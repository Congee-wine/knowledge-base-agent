"""Refresh built-in AI manager preset questions.

Revision ID: 20260805_0014
Revises: 20260801_0013
Create Date: 2026-08-05
"""

from alembic import op


revision = "20260805_0014"
down_revision = "20260801_0013"
branch_labels = None
depends_on = None


BUILTIN_AGENT_ID = "00000000-0000-0000-0000-000000000001"
CURRENT_QUESTIONS = (
    ("00000000-0000-0000-0000-000000000101", "支持上传哪些文件格式？"),
    ("00000000-0000-0000-0000-000000000102", "如何新建文件夹并整理资料？"),
    ("00000000-0000-0000-0000-000000000103", "资料上传后，什么时候可以开始提问？"),
    ("00000000-0000-0000-0000-000000000104", "如何让 AI 管家基于我的资料回答问题？"),
    ("00000000-0000-0000-0000-000000000105", "为什么 AI 没有引用或没有找到相关资料？"),
    ("00000000-0000-0000-0000-000000000106", "如何查看、移动或删除已上传的资料？"),
)
PREVIOUS_QUESTIONS = (
    ("00000000-0000-0000-0000-000000000101", "产品品类多，生产资料一大堆，如何快速找到生产信息？"),
    ("00000000-0000-0000-0000-000000000102", "怎么维护知识库，才能更轻松地完成合同等文本工作？"),
    ("00000000-0000-0000-0000-000000000103", "如何搭建智能客服应用？"),
    ("00000000-0000-0000-0000-000000000104", "我创建的文档，其他同事可以看到吗？"),
    ("00000000-0000-0000-0000-000000000105", "如何一次性把现有资料放到知识库中？"),
    ("00000000-0000-0000-0000-000000000106", "支持在线编辑吗？"),
    ("00000000-0000-0000-0000-000000000107", "支持上传文件夹吗？"),
)


def upgrade() -> None:
    _replace_questions(CURRENT_QUESTIONS)


def downgrade() -> None:
    _replace_questions(PREVIOUS_QUESTIONS)


def _replace_questions(questions: tuple[tuple[str, str], ...]) -> None:
    op.execute(
        "DELETE FROM agent_preset_questions WHERE agent_id = '{}'".format(BUILTIN_AGENT_ID)
    )
    for display_order, (question_id, content) in enumerate(questions):
        op.execute(
            """INSERT INTO agent_preset_questions (id, agent_id, content, display_order, created_at)
            VALUES ('{question_id}', '{agent_id}', '{content}', {display_order}, now())""".format(
                question_id=question_id,
                agent_id=BUILTIN_AGENT_ID,
                content=content.replace("'", "''"),
                display_order=display_order,
            )
        )
