"""Behavioral invariants of the separately installable skill helper/package."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.package_skill import SKILL, build, validate_bundle

spec = importlib.util.spec_from_file_location("skill_checkpoint", SKILL / "scripts" / "checkpoint.py")
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


class SkillBundleTests(unittest.TestCase):
    def test_installed_zip_works_without_legacy_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = build(root / "get-hired-now.zip")
            with zipfile.ZipFile(archive) as bundle:
                self.assertIn("get-hired-now/SKILL.md", bundle.namelist())
                self.assertIn("get-hired-now/LICENSE", bundle.namelist())
                self.assertFalse(any("get_hired_now" in name for name in bundle.namelist()))
                bundle.extractall(root / "installed")
            script = root / "installed" / "get-hired-now" / "scripts" / "checkpoint.py"
            private = root / "candidate-workspace"
            result = subprocess.run([sys.executable, "-I", str(script), "init", "--workspace", str(private)],
                                    cwd=root, capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(result.stdout)["saved"])
            value = json.loads((private / "state.json").read_text())
            self.assertIsNone(value["candidate"])
            self.assertEqual(value["permissions"]["mode"], "REVIEW")
            self.assertEqual(value["jobs"], {})
            value["candidate"] = {"revision": 1, "facts": {"sample": {"value": "supplied", "source": "user:test"}}}
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps(value))
            subprocess.run([sys.executable, "-I", str(script), "save", "--workspace", str(private),
                            "--input", str(proposal), "--expected-revision", "0"],
                           cwd=root, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads((private / "state.json").read_text())["revision"], 1)
            value = json.loads((private / "state.json").read_text())
            value["rounds"] = {"fictional-batch": {"elapsed_seconds": 60, "active_seconds": None}}
            proposal.write_text(json.dumps(value))
            subprocess.run([sys.executable, "-I", str(script), "save", "--workspace", str(private),
                            "--input", str(proposal), "--expected-revision", "1"],
                           cwd=root, capture_output=True, text=True, check=True)
            reporter = script.with_name("round_report.py")
            before = (private / "state.json").read_bytes()
            result = subprocess.run([sys.executable, "-I", str(reporter), "--workspace", str(private),
                                     "--batch", "fictional-batch"], cwd=root, capture_output=True,
                                    text=True, check=True)
            self.assertEqual(json.loads(result.stdout)["counts"]["confirmed"], 0)
            self.assertEqual((private / "state.json").read_bytes(), before)

    def test_all_linked_skill_references_are_self_contained(self):
        validate_bundle()


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.blank = json.loads((SKILL / "assets" / "state.example.json").read_text())
        checkpoint.atomic_write(self.root / "state.json", self.blank)

    def test_stale_writer_cannot_replace_new_state(self):
        checkpoint.save(self.root, self.blank, 0)
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, self.blank, 0)
        self.assertEqual(json.loads((self.root / "state.json").read_text())["revision"], 1)

    def test_exclusive_writer_lock(self):
        with checkpoint.lock(self.root):
            with self.assertRaises(ValueError):
                checkpoint.save(self.root, self.blank, 0)
        self.assertFalse((self.root / ".checkpoint.lock").exists())

    def test_submission_without_exact_receipt_rejected(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "SUBMITTED", "receipts": []}
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, proposal, 0)
        self.assertEqual(json.loads((self.root / "state.json").read_text()), self.blank)

    def test_attempt_must_be_durable(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "SUBMITTING"}
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, proposal, 0)

    def test_receipts_and_audit_history_cannot_be_erased(self):
        proposal = copy.deepcopy(self.blank)
        proposal["events"] = [{"kind": "fictional-receipt"}]
        proposal["jobs"]["fictional-job"] = {"stage": "SUBMITTED", "receipts": [
            {"job_key": "fictional-job", "outcome": "accepted", "evidence": "fictional:acceptance"}]}
        saved = checkpoint.save(self.root, proposal, 0)
        altered = copy.deepcopy(saved)
        altered["events"] = []
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, altered, 1)
        altered = copy.deepcopy(saved)
        altered["jobs"]["fictional-job"]["stage"] = "READY_FOR_REVIEW"
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, altered, 1)

    def test_unresolved_attempt_cannot_be_reopened_without_evidence(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "UNRESOLVED", "attempts": [{"id": "fictional-attempt"}]}
        saved = checkpoint.save(self.root, proposal, 0)
        saved["jobs"]["fictional-job"]["stage"] = "HUMAN_REQUIRED"
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, saved, 1)

    def test_no_candidate_storage_inside_installed_skill(self):
        (self.root / "SKILL.md").write_text("synthetic installed skill")
        with self.assertRaises(ValueError):
            checkpoint.workspace(self.root / "candidate")

    def test_candidate_identity_cannot_be_changed_or_removed(self):
        proposal = copy.deepcopy(self.blank)
        proposal["candidate_id"] = "fictional-candidate-a"
        saved = checkpoint.save(self.root, proposal, 0)
        for replacement in ("fictional-candidate-b", None):
            altered = copy.deepcopy(saved)
            altered["candidate_id"] = replacement
            with self.assertRaises(ValueError):
                checkpoint.save(self.root, altered, 1)

    def test_attempt_evidence_cannot_be_erased_after_resolution(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "HUMAN_REQUIRED", "attempts": [
            {"id": "fictional-attempt", "destination": "https://employer.example.invalid/apply"}]}
        saved = checkpoint.save(self.root, proposal, 0)
        saved["jobs"]["fictional-job"]["attempts"] = []
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, saved, 1)

    def test_no_second_attempt_while_first_is_unresolved(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "UNRESOLVED", "attempts": [{"id": "first"}]}
        saved = checkpoint.save(self.root, proposal, 0)
        saved["jobs"]["fictional-job"]["attempts"].append({"id": "second"})
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, saved, 1)

    def test_duplicate_attempt_ids_are_rejected(self):
        proposal = copy.deepcopy(self.blank)
        proposal["jobs"]["fictional-job"] = {"stage": "SUBMITTING", "attempts": [
            {"id": "same"}, {"id": "same"}]}
        with self.assertRaises(ValueError):
            checkpoint.save(self.root, proposal, 0)


if __name__ == "__main__":
    unittest.main()
