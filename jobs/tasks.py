import asyncio
import base64
from jobs.celery_app import celery_app
from jobs.storage import update_job
from agents.supervisor.agent import supervisor_agent
from agents.pitch_deck.agent import pitch_deck_agent
from agents.video_pitch.agent import video_pitch_agent
from core.utils import (
    convert_pdf_to_images,
    getbase64,
    handle_complete,
    handle_input_slides,
    handle_video_pitch,
    transcribe_audio_bytes,
)
from core.pitch_preprocess import preprocess_pitch_text
from core.pitch_claims import extract_claims_from_text
from agents.pitch_deck.helpers import extract_investor_personas


def _b64_to_bytes(value: str) -> bytes:
    return base64.b64decode(value.encode("utf-8"))


@celery_app.task(name="jobs.analyze_complete", bind=True)
def analyze_complete_job(self, job_id: str, payload: dict):
    try:
        update_job(job_id, status="processing", progress="Analyzing data")

        images = convert_pdf_to_images(_b64_to_bytes(payload["pdf_b64"]))
        encoded_images = [{'imageByte': getbase64(image)} for image in images]
        kwargs, _run_id = asyncio.run(handle_complete(encoded_images))
        result = supervisor_agent.invoke(**kwargs)

        out = {
            'summary': result['summary'],
            'scorecard': result['scorecard'],
            'overall_score': result.get('overall_score', 0),
            'claim_assumptions': result.get('claim_assumptions'),
            'investor_simulation': result.get('investor_simulation'),
            'market_research': result.get('market_research')
        }
        if result.get('github_url'):
            out['github_details'] = result.get('github_details')

        update_job(job_id, status="completed", progress="Analysis complete", result=out)
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))


@celery_app.task(name="jobs.analyze_pitch_deck", bind=True)
def analyze_pitch_deck_job(self, job_id: str, payload: dict):
    try:
        update_job(job_id, status="processing", progress="Analyzing pitch deck")

        images = convert_pdf_to_images(_b64_to_bytes(payload["pdf_b64"]))
        encoded_images = [{'imageByte': getbase64(image)} for image in images]
        kwargs, _run_id = asyncio.run(handle_input_slides(encoded_images))
        result = pitch_deck_agent.invoke(**kwargs)

        out = {
            'scorecard': result.get('scorecard'),
            'summary': result.get('summary'),
            'overall_score': result.get('overall_score', 0),
            'claim_assumptions': result.get('claim_assumptions'),
            'investor_simulation': result.get('investor_simulation'),
        }
        update_job(job_id, status="completed", progress="Analysis complete", result=out)
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))


@celery_app.task(name="jobs.analyze_video_pitch", bind=True)
def analyze_video_pitch_job(self, job_id: str, payload: dict):
    try:
        update_job(job_id, status="processing", progress="Transcribing video")

        transcript = transcribe_audio_bytes(
            _b64_to_bytes(payload["file_b64"]),
            payload.get("filename", "pitch"),
            payload.get("content_type"),
        )
        if not transcript:
            raise ValueError("Transcription failed to extract text.")

        update_job(job_id, status="processing", progress="Analyzing transcript")
        kwargs, _run_id = asyncio.run(handle_video_pitch(transcript))
        result = video_pitch_agent.invoke(**kwargs)

        if "analysis" not in result:
            raise ValueError("Video pitch analysis failed.")

        update_job(
            job_id,
            status="completed",
            progress="Analysis complete",
            result={"transcript": transcript, "analysis": result["analysis"]},
        )
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))


@celery_app.task(name="jobs.extract_claims", bind=True)
def extract_claims_job(self, job_id: str, payload: dict):
    try:
        update_job(job_id, status="processing", progress="Extracting claims")

        content_type = payload.get("content_type")
        if content_type and content_type.startswith(("video/", "audio/")):
            transcript = transcribe_audio_bytes(
                _b64_to_bytes(payload["file_b64"]),
                payload.get("filename", "pitch"),
                content_type,
            )
            preprocess = preprocess_pitch_text(transcript)
            claims = extract_claims_from_text(preprocess.normalized_text)
            investor_modes = extract_investor_personas(preprocess.normalized_text)
            result = {
                "source_type": "video",
                "transcript": transcript,
                "normalized_text": preprocess.normalized_text,
                "sections": preprocess.sections,
                "claim_assumptions": claims.model_dump(),
                "investor_modes": investor_modes.model_dump(),
            }
            update_job(job_id, status="completed", progress="Claims extracted", result=result)
            return

        if content_type == "application/pdf":
            images = convert_pdf_to_images(_b64_to_bytes(payload["file_b64"]))
            encoded_images = [{'imageByte': getbase64(image)} for image in images]
            kwargs, _run_id = asyncio.run(handle_input_slides(encoded_images))
            response = pitch_deck_agent.invoke(**kwargs)
            source_text = f"Summary: {response.get('summary')}\nSlides: {response.get('slide_content', [])}"
            preprocess = preprocess_pitch_text(source_text)
            claims = response.get("claim_assumptions") or extract_claims_from_text(
                preprocess.normalized_text
            ).model_dump()
            investor_modes = extract_investor_personas(preprocess.normalized_text).model_dump()

            result = {
                "source_type": "deck",
                "normalized_text": preprocess.normalized_text,
                "sections": preprocess.sections,
                "claim_assumptions": claims,
                "investor_modes": investor_modes,
            }
            update_job(job_id, status="completed", progress="Claims extracted", result=result)
            return

        raise ValueError("Unsupported file type.")
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
