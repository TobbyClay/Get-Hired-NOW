"""Batch reporting measures recorded events without promoting attempts to receipts."""

import copy
import importlib.util
import unittest

from tools.package_skill import SKILL

spec = importlib.util.spec_from_file_location("skill_round_report", SKILL / "scripts" / "round_report.py")
round_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(round_report)


class RoundReportTests(unittest.TestCase):
    def setUp(self):
        self.state = {"schema_version": 1, "jobs": {
            "one": {"stage": "EVALUATED", "receipts": []},
            "two": {"stage": "UNRESOLVED", "receipts": []}},
            "events": [], "rounds": {"today": {"elapsed_seconds": 1800, "active_seconds": None}}}

    def event(self, key, kind, **extra):
        self.state["events"].append(dict(batch_id="today", job_key=key, kind=kind,
                                         evidence="fictional:evidence", **extra))

    def receipt(self, key, batch="today", **extra):
        self.state["jobs"][key]["receipts"].append(dict(job_key=key, outcome="accepted",
                                                       evidence="fictional:receipt",
                                                       confirmed_in_batch=batch, **extra))

    def test_duplicate_sightings_are_not_extra_screens_or_confirmations(self):
        for source in ("connector", "direct", "direct"):
            self.event("one", "lead_observed", source_lane=source)
            self.event("one", "posting_screened", source_lane=source, role_family="operations")
        self.receipt("one")
        self.receipt("one")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["raw_discoveries"], 3)
        self.assertEqual(result["counts"]["unique_discoveries"], 1)
        self.assertEqual(result["counts"]["screened"], 1)
        self.assertEqual(result["counts"]["confirmed"], 1)
        self.assertEqual(result["source_coverage"], {"connector": 1, "direct": 1})
        self.assertEqual(result["family_coverage"], {"operations": 1})

    def test_metadata_rows_and_unreferenced_events_do_not_become_screens(self):
        self.state["events"] = [dict(batch_id="today", job_key="one", kind="posting_screened"),
                                 dict(batch_id="today", job_key="missing", kind="posting_screened",
                                      evidence="fictional:evidence")]
        self.assertEqual(round_report.report(self.state, "today")["counts"]["screened"], 0)

    def test_upload_and_autosave_are_not_final_submit(self):
        self.event("one", "resume_uploaded")
        self.event("one", "candidate_entered")
        self.assertEqual(round_report.report(self.state, "today")["counts"]["attempted"], 0)

    def test_accepted_label_without_receipt_remains_unresolved(self):
        self.event("one", "submit_clicked")
        self.event("one", "attempt_result", outcome="accepted")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["confirmed"], 0)
        self.assertEqual(result["counts"]["unresolved"], 1)

    def test_wrong_role_receipt_does_not_resolve_attempt(self):
        self.event("one", "submit_clicked")
        self.state["jobs"]["one"]["receipts"] = [dict(job_key="two", outcome="accepted",
                                                           evidence="fictional:receipt", confirmed_in_batch="today")]
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["confirmed"], 0)
        self.assertEqual(result["counts"]["unresolved"], 1)

    def test_late_receipt_is_separate_from_new_confirmed_submit(self):
        self.event("one", "submit_clicked")
        self.state["events"].append(dict(batch_id="yesterday", job_key="two", kind="submit_clicked",
                                         evidence="fictional:prior-submit"))
        self.receipt("one")
        self.receipt("two")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["attempted"], 1)
        self.assertEqual(result["counts"]["confirmed"], 2)
        self.assertEqual(result["counts"]["confirmed_from_prior_attempts"], 1)
        self.assertEqual(result["counts"]["confirmed_from_current_submits"], 1)
        self.assertEqual(result["counts"]["unresolved"], 0)

    def test_receipt_without_a_recorded_submit_does_not_invent_a_cohort(self):
        self.receipt("one")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["confirmed"], 1)
        self.assertEqual(result["counts"]["confirmed_from_prior_attempts"], 0)
        self.assertEqual(result["counts"]["confirmed_from_current_submits"], 0)
        self.assertEqual(result["counts"]["confirmed_submit_cohort_unknown"], 1)

    def test_old_receipts_and_other_batches_do_not_inflate_today(self):
        self.receipt("one", batch="yesterday")
        self.state["events"].append(dict(batch_id="yesterday", job_key="two", kind="submit_clicked",
                                         evidence="fictional:evidence"))
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["confirmed"], 0)
        self.assertEqual(result["counts"]["attempted"], 0)

    def test_failed_and_security_outcomes_are_separate(self):
        self.event("one", "submit_clicked")
        self.event("two", "submit_clicked")
        self.event("one", "attempt_result", outcome="unresolved")
        self.event("one", "attempt_result", outcome="failed_validation", reason="required_field")
        self.event("two", "attempt_result", outcome="security_blocked", reason="captcha")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["failed_validation"], 1)
        self.assertEqual(result["counts"]["security_blocked"], 1)
        self.assertEqual(result["counts"]["unresolved"], 0)
        self.assertEqual(result["blocker_reasons"], {"captcha": 1, "required_field": 1})

    def test_unmeasured_time_is_not_inferred_and_report_is_read_only(self):
        self.receipt("one")
        before = copy.deepcopy(self.state)
        result = round_report.report(self.state, "today")
        self.assertEqual(result["confirmations_per_elapsed_hour"], 2)
        self.assertIsNone(result["confirmations_per_active_hour"])
        self.assertEqual(self.state, before)

    def test_invalid_time_and_unknown_batch_are_rejected(self):
        for value in (-1, True, float("nan"), float("inf"), "30"):
            self.state["rounds"]["today"]["elapsed_seconds"] = value
            with self.assertRaises(ValueError):
                round_report.report(self.state, "today")
        self.state["rounds"]["today"] = {"elapsed_seconds": 10, "active_seconds": 30}
        with self.assertRaises(ValueError):
            round_report.report(self.state, "today")
        with self.assertRaises(ValueError):
            round_report.report(self.state, "unknown")

    def test_pre_submit_blocker_is_reported_without_becoming_an_attempt(self):
        self.event("one", "role_conditional")
        self.event("one", "role_blocked", reason="missing_required_fact")
        result = round_report.report(self.state, "today")
        self.assertEqual(result["counts"]["conditional"], 1)
        self.assertEqual(result["counts"]["attempted"], 0)
        self.assertEqual(result["blocker_reasons"], {"missing_required_fact": 1})
        self.event("one", "blocker_resolved")
        self.assertEqual(round_report.report(self.state, "today")["blocker_reasons"], {})


if __name__ == "__main__":
    unittest.main()
