import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    @patch("main.video_pitch_agent")
    def test_analyze_video_pitch_text(self, video_pitch_agent):
        video_pitch_agent.invoke.return_value = {
            "analysis": {"filter_ai_score": 80, "investor_ready_status": "Investor ready"}
        }
        response = self.client.post(
            "/analyze-video-pitch-text",
            json={"transcript": "We solve logistics for SMBs."},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcript"], "We solve logistics for SMBs.")
        self.assertIn("analysis", data)

    def test_analyze_video_pitch_upload_invalid_type(self):
        response = self.client.post(
            "/analyze-video-pitch",
            files={"file": ("pitch.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    @patch("main.analyze_video_pitch_job")
    @patch("main.create_job")
    def test_analyze_video_pitch_upload_success(self, create_job, analyze_video_pitch_job):
        create_job.return_value = type("Job", (), {"id": "job-123", "status": "pending"})()
        response = self.client.post(
            "/analyze-video-pitch",
            files={"file": ("pitch.mp3", io.BytesIO(b"audio"), "audio/mpeg")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["job_id"], "job-123")
        self.assertEqual(data["status"], "pending")
        analyze_video_pitch_job.apply_async.assert_called_once()


if __name__ == "__main__":
    unittest.main()
