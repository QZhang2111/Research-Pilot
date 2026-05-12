import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.job_records import create_job_record, jobs_dir, list_job_records, validate_job_record


def valid_job_record(job_id: str = "job-valid"):
    return {
        "id": job_id,
        "type": "paper_search",
        "project": "DemoProject",
        "status": "queued",
        "created_at": "2026-05-12T00:00:00Z",
        "updated_at": "2026-05-12T00:00:00Z",
        "owner": "agent",
        "human_gate": "required_before_graph_update",
        "truth_boundary": "execution_state_only",
        "inputs": {"gap_id": "RL0"},
        "artifacts": [],
        "result_summary": "Queued search. No graph truth changed.",
    }


class JobRecordsTest(unittest.TestCase):
    def test_create_job_record_persists_execution_state_only_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            record = create_job_record(
                root,
                job_type="paper_search",
                project="DemoProject",
                status="queued",
                inputs={"gap_id": "RL0"},
                artifacts=[],
                result_summary="Queued search. No graph truth changed.",
            )
            records = list_job_records(root)

        self.assertTrue(record["id"].startswith("job-"))
        self.assertEqual(records[0]["id"], record["id"])
        self.assertEqual(records[0]["human_gate"], "required_before_graph_update")
        self.assertEqual(records[0]["truth_boundary"], "execution_state_only")

    def test_create_job_record_does_not_overwrite_same_second_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("tools.job_records.now_string", return_value="2026-05-12T00:00:00Z"):
                first = create_job_record(
                    root,
                    job_type="paper_search",
                    project="DemoProject",
                    status="queued",
                    result_summary="First job.",
                )
                second = create_job_record(
                    root,
                    job_type="paper_search",
                    project="DemoProject",
                    status="queued",
                    result_summary="Second job.",
                )
            records = list_job_records(root)
            summaries = [record["result_summary"] for record in records]

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(records), 2)
        self.assertCountEqual(summaries, ["First job.", "Second job."])

    def test_create_job_record_rejects_falsey_invalid_container_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "inputs"):
                create_job_record(
                    root,
                    job_type="paper_search",
                    project="DemoProject",
                    status="queued",
                    inputs=[],
                    result_summary="Invalid inputs.",
                )

            with self.assertRaisesRegex(ValueError, "artifacts"):
                create_job_record(
                    root,
                    job_type="paper_search",
                    project="DemoProject",
                    status="queued",
                    artifacts={},
                    result_summary="Invalid artifacts.",
                )

    def test_jobs_dir_expands_home_for_create_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = Path("~/workspace")
            with patch.dict("os.environ", {"HOME": str(home)}):
                record = create_job_record(
                    root,
                    job_type="paper_search",
                    project="DemoProject",
                    status="queued",
                    result_summary="Home-expanded job.",
                )
                records = list_job_records(root)
                directory = jobs_dir(root)

        self.assertEqual(directory, (home / "workspace").resolve() / ".research-pilot" / "jobs")
        self.assertEqual(records[0]["id"], record["id"])
        self.assertEqual(records[0]["path"], f".research-pilot/jobs/{record['id']}.json")

    def test_list_job_records_skips_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_job_record(
                root,
                job_type="paper_search",
                project="DemoProject",
                status="queued",
                result_summary="Valid job.",
            )
            jobs_dir = root / ".research-pilot" / "jobs"
            (jobs_dir / "job-corrupt.json").write_text("{not-json", encoding="utf-8")

            records = list_job_records(root)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["result_summary"], "Valid job.")

    def test_list_job_records_skips_non_utf8_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_job_record(
                root,
                job_type="paper_search",
                project="DemoProject",
                status="queued",
                result_summary="Valid job.",
            )
            jobs_dir = root / ".research-pilot" / "jobs"
            (jobs_dir / "job-non-utf8.json").write_bytes(b"\xff\xfe\x00\x00")

            records = list_job_records(root)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["result_summary"], "Valid job.")

    def test_list_job_records_skips_invalid_truth_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / ".research-pilot" / "jobs"
            jobs_dir.mkdir(parents=True)
            (jobs_dir / "job-invalid.json").write_text(
                "{"
                '"id":"job-invalid",'
                '"type":"paper_search",'
                '"project":"DemoProject",'
                '"status":"queued",'
                '"human_gate":"required_before_graph_update",'
                '"truth_boundary":"graph_truth_changed"'
                "}",
                encoding="utf-8",
            )

            records = list_job_records(root)

        self.assertEqual(records, [])

    def test_validate_job_record_rejects_missing_required_field(self):
        record = valid_job_record()
        del record["project"]

        result = validate_job_record(record)

        self.assertFalse(result["valid"])
        self.assertTrue(any("project" in error for error in result["errors"]))

    def test_list_job_records_skips_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / ".research-pilot" / "jobs"
            jobs_dir.mkdir(parents=True)
            record = valid_job_record("job-missing-project")
            del record["project"]
            (jobs_dir / "job-missing-project.json").write_text(json.dumps(record), encoding="utf-8")

            records = list_job_records(root)

        self.assertEqual(records, [])

    def test_list_job_records_skips_filename_id_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / ".research-pilot" / "jobs"
            jobs_dir.mkdir(parents=True)
            record = valid_job_record("job-b")
            (jobs_dir / "job-a.json").write_text(json.dumps(record), encoding="utf-8")

            records = list_job_records(root)

        self.assertEqual(records, [])

    def test_validate_job_record_rejects_graph_truth_boundary(self):
        record = {
            "id": "job-20260512T000000Z",
            "type": "paper_search",
            "project": "DemoProject",
            "status": "queued",
            "human_gate": "required_before_graph_update",
            "truth_boundary": "graph_truth_changed",
        }

        result = validate_job_record(record)

        self.assertFalse(result["valid"])
        self.assertTrue(any("truth_boundary" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
