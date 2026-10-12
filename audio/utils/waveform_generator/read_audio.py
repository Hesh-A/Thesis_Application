from pathlib import Path

from scipy.io import wavfile

AUDIO_PATH = Path(__file__).resolve().parents[2] / "sa1_.wav"


def read_audio(file_path: Path):
    sample_rate, audio_data = wavfile.read(file_path)
    duration_seconds = len(audio_data) / sample_rate

    print(f"File: {file_path.name}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Audio shape: {audio_data.shape}")
    print(f"Data type: {audio_data.dtype}")
    print(f"Duration: {duration_seconds:.2f} seconds")

    return sample_rate, audio_data


