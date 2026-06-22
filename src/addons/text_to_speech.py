# from kokoro import KPipeline
# #from IPython.display import display, Audio
# import soundfile as sf
# import torch

# pipeline = KPipeline(lang_code='a')
# def text_to_speech(text:str):
#     """converts Clara's response from text to audio format"""
#     generator = pipeline(text, voice='af_heart')
#     for i, (gs, ps, audio) in enumerate(generator):
#         print(i, gs, ps)
#         #display(Audio(data=audio, rate=24000, autoplay=i==0))
#         sf.write(f'{i}.wav', audio, 24000)



import io
import base64
import numpy as np
import soundfile as sf
from kokoro import KPipeline

# Initialize the pipeline once globally at the module level
pipeline = KPipeline(lang_code='a')

def text_to_speech(text: str) -> str:
    """
    Converts Clara's response text to audio format in memory.
    Returns a Base64-encoded string of the WAV audio data.
    """
    # Clean markdown formatting so Clara does not read asterisks aloud
    cleaned_text = text.replace("*", "").replace("#", "").strip()
    
    generator = pipeline(cleaned_text, voice='af_heart')
    
    # Collect all audio segments into a list
    audio_chunks = []
    for _, _, audio in generator:
        audio_chunks.append(audio)
        
    if not audio_chunks:
        return ""
        
    # Concatenate multiple sentence fragments into a single audio array
    full_audio = np.concatenate(audio_chunks)
    
    # Create an in-memory byte stream buffer
    byte_io = io.BytesIO()
    
    # Write the raw audio array directly into the buffer as a standard WAV file
    sf.write(byte_io, full_audio, 24000, format='WAV')
    
    # Retrieve raw bytes and translate them into a Base64 text string
    byte_io.seek(0)
    audio_bytes = byte_io.read()
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    
    return base64_audio
