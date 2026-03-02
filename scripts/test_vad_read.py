"""Quick diagnostic: test xread + VAD on a live audio chunk."""
import asyncio
import base64
import redis.asyncio as aioredis

STREAM_ID = "e737a0f6-c475-4414-af2e-3e7bba855d6a"

async def main():
    r = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
    
    # Test xread
    entries = await r.xread(
        {f"audio_chunks:{STREAM_ID}": "0"},
        count=5,
        block=0,
    )
    
    if not entries:
        print("No entries returned from xread!")
        await r.close()
        return
    
    stream_name, messages = entries[0]
    print(f"Stream: {stream_name}, messages: {len(messages)}")
    
    for entry_id, fields in messages:
        pcm_b64 = fields.get("pcm_b64", "")
        pcm = base64.b64decode(pcm_b64) if pcm_b64 else b""
        nonzero = sum(1 for b in pcm if b != 0)
        print(f"  {entry_id}: {len(pcm)} bytes, {nonzero} non-zero bytes")
    
    # Get a recent chunk with actual audio
    latest = await r.xrevrange(
        f"audio_chunks:{STREAM_ID}", "+", "-", count=1
    )
    if latest:
        entry_id, fields = latest[0]
        pcm_b64 = fields.get("pcm_b64", "")
        pcm = base64.b64decode(pcm_b64) if pcm_b64 else b""
        nonzero = sum(1 for b in pcm if b != 0)
        print(f"\nLatest chunk: {entry_id}: {len(pcm)} bytes, {nonzero} non-zero bytes")
        
        # Try running Silero VAD on it
        try:
            from vad.silero_vad import SileroVADModel
            model = SileroVADModel()
            model.load()
            score = model.classify_sync(pcm)
            print(f"VAD score: {score}")
        except Exception as e:
            print(f"VAD model error: {e}")
    
    # Check speech_chunks
    speech_len = await r.xlen(f"speech_chunks:{STREAM_ID}")
    print(f"\nspeech_chunks length: {speech_len}")
    
    await r.close()

asyncio.run(main())
