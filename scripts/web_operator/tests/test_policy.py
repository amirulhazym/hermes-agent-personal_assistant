import unittest

from scripts.web_operator.contracts import ActionClass, ActionIntent, PolicyVerdict
from scripts.web_operator.policy import PolicyEngine


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()

    def _intent(self, cls: ActionClass, **params) -> ActionIntent:
        return ActionIntent(
            task_id="t1",
            action_id="a1",
            owner_id="o1",
            action_class=cls,
            target="https://example.com",
            parameters=params,
            state_digest="s1",
        )

    def test_allow_public(self):
        d = self.engine.classify_action(self._intent(ActionClass.PUBLIC_READ))
        self.assertEqual(d.verdict, PolicyVerdict.ALLOW)

    def test_pause_external_send(self):
        d = self.engine.classify_action(self._intent(ActionClass.EXTERNAL_SEND))
        self.assertEqual(d.verdict, PolicyVerdict.PAUSE)
        self.assertTrue(d.requires_approval)

    def test_deny_shell_and_secrets(self):
        for cls in (
            ActionClass.SHELL_SIDE_EFFECT,
            ActionClass.SECRET_EXPOSURE,
            ActionClass.INFRASTRUCTURE_CHANGE,
            ActionClass.PAID_SERVICE_ENABLE,
            ActionClass.EXPENSIVE_MODEL_SWITCH,
        ):
            d = self.engine.classify_action(self._intent(cls))
            self.assertEqual(d.verdict, PolicyVerdict.DENY, cls)

    def test_bulk_delete_denied(self):
        d = self.engine.classify_action(
            self._intent(ActionClass.DELETE_OR_OVERWRITE, bulk=True)
        )
        self.assertEqual(d.verdict, PolicyVerdict.DENY)

    def test_authorize_requires_matching_digest(self):
        action = self._intent(ActionClass.FORM_SUBMIT)
        d = self.engine.authorize(action, None, "s1")
        self.assertEqual(d.verdict, PolicyVerdict.PAUSE)


if __name__ == "__main__":
    unittest.main()
