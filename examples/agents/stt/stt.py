import asyncio
import livekit.rtc as rtc
from livekit import agents
from livekit.processors.vad import VADProcessor, VAD
from livekit.processors.google import SpeechRecognitionProcessor
from typing import AsyncIterator


async def stt_agent(params: agents.Job.AgentParams):

    async def process_track(track: rtc.Track):
        audio_stream = rtc.AudioStream(track)
        vad_processor = VADProcessor(silence_threshold_ms=250)
        stt_processor = SpeechRecognitionProcessor(
            google_credentials_filepath="google.json")

        async def vad_result_loop(queue: AsyncIterator[VAD.Event]):
            async for event in queue:
                if event.type == "voice_finished":
                    frames = event.frames
                    stt_processor.push(frames)

        async def stt_result_loop(queue: AsyncIterator[AsyncIterator[agents.STTProcessor.Event]]):
            async for event_iterator in queue:
                async for event in event_iterator:
                    print(event)

        asyncio.create_task(stt_result_loop(queue=stt_processor.stream()))
        asyncio.create_task(vad_result_loop(queue=vad_processor.stream()))

        async for frame in audio_stream:
            vad_processor.push(frame)

    @params.room.on("data_received")
    def on_data_received(data: str, participant: rtc.RemoteParticipant):
        print(f"Data Received: {data}")

    @params.room.on("track_available")
    def on_track_available(publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == rtc.TrackKind.KIND_AUDIO:
            publication.set_subscribed(True)

    @params.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind != rtc.TrackKind.KIND_AUDIO:
            return

        asyncio.create_task(process_track(track))