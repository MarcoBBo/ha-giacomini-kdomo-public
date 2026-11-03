"""Offline regression tests, runnable with Python's standard library alone."""

import importlib.util
import sys
import types
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "kdomo"
PACKAGE = "_kdomo_regression"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(f"{PACKAGE}.models", ROOT / "models.py")
assert spec is not None and spec.loader is not None
models = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = models
spec.loader.exec_module(models)


def state(**changes):
    values = {
        "mode": "2",
        "status": "1",
        "program": "0",
        "currentsetpoint": "21",
        "fancoil": "0",
        "scale": "0",
    }
    values.update({k: str(v) for k, v in changes.items()})
    return models.Snapshot(values, dict.fromkeys(values, 1000), online=True)


class AutoConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.before = state()
        self.payload = models.settings_payload(self.before, operation="auto")
        self.after = state(mode=1, currentsetpoint=19)
        self.after = replace(self.after, timestamps=dict.fromkeys(self.after.values, 1003))

    def confirm(self, after, payload=None, **kwargs):
        return models.fresh_confirmation(self.before, after, payload or self.payload, 1002, **kwargs)

    def test_auto_accepts_recalculated_target(self):
        self.assertTrue(self.confirm(self.after, allow_auto_setpoint=True))

    def test_manual_never_accepts_different_target(self):
        self.assertFalse(self.confirm(self.after))

    def test_auto_rejects_invalid_or_missing_target(self):
        for value in (None, "nan", "inf", "invalid", "36"):
            values = dict(self.after.values)
            if value is None:
                del values["currentsetpoint"]
            else:
                values["currentsetpoint"] = value
            with self.subTest(value=value):
                self.assertFalse(self.confirm(replace(self.after, values=values), allow_auto_setpoint=True))

    def test_auto_still_checks_other_fields_and_freshness(self):
        for key, value in (("mode", "2"), ("status", "0"), ("program", "1"), ("fancoil", "1")):
            with self.subTest(key=key):
                self.assertFalse(
                    self.confirm(
                        replace(self.after, values={**self.after.values, key: value}),
                        allow_auto_setpoint=True,
                    )
                )
        self.assertFalse(self.confirm(replace(self.after, online=False), allow_auto_setpoint=True))
        self.assertFalse(self.confirm(replace(self.after, error=True), allow_auto_setpoint=True))
        self.assertFalse(
            self.confirm(
                replace(self.after, timestamps={**self.after.timestamps, "mode": 1000}),
                allow_auto_setpoint=True,
            )
        )
        self.assertFalse(
            self.confirm(
                replace(self.after, values={**self.after.values, "scale": "1"}), allow_auto_setpoint=True
            )
        )

    def test_changed_status_also_requires_fresh_timestamp(self):
        before = state(status=0)
        payload = models.settings_payload(before, operation="auto")
        after = replace(self.after, timestamps={**self.after.timestamps, "status": 1000})
        self.assertFalse(models.fresh_confirmation(before, after, payload, 1002, allow_auto_setpoint=True))


if __name__ == "__main__":
    unittest.main()
