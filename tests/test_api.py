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

    @patch("main.transcribe_audio_bytes", return_value="We solve logistics for SMBs.")
    @patch("main.video_pitch_agent")
    def test_analyze_video_pitch_upload_success(self, video_pitch_agent, _transcriber):
        video_pitch_agent.invoke.return_value = {
            "analysis": {"filter_ai_score": 72, "investor_ready_status": "Investor ready"}
        }
        response = self.client.post(
            "/analyze-video-pitch",
            files={"file": ("pitch.mp3", io.BytesIO(b"audio"), "audio/mpeg")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcript"], "We solve logistics for SMBs.")
        self.assertIn("analysis", data)


if __name__ == "__main__":
    unittest.main()
