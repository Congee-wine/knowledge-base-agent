import unittest

from services.agent_identity import (
    build_public_profile,
    contains_self_disclosure,
    render_public_profile_answer,
    requires_public_profile_answer,
)


class AgentIdentityTests(unittest.TestCase):
    def test_model_question_is_routed_to_public_profile(self) -> None:
        self.assertTrue(requires_public_profile_answer("你背后调用的是什么模型？"))
        self.assertTrue(requires_public_profile_answer("What model are you using?"))

    def test_public_response_never_discloses_model_configuration(self) -> None:
        answer = render_public_profile_answer(build_public_profile("AI 管家", None, True), "你是 DeepSeek-V3 吗？")

        self.assertNotIn("DeepSeek", answer)
        self.assertNotIn("模型", answer)
        self.assertIn("内部技术配置", answer)

    def test_detects_model_self_disclosure(self) -> None:
        self.assertTrue(contains_self_disclosure("我是 DeepSeek-V3。"))
        self.assertFalse(contains_self_disclosure("我是 AI 管家，负责整理资料。"))


if __name__ == "__main__":
    unittest.main()
