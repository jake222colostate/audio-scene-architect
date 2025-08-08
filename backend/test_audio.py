import pytest

audiocraft = pytest.importorskip("audiocraft")
from audiocraft.models import musicgen
from audiocraft.data.audio import audio_write


@pytest.mark.skip(reason="integration example; skip during unit tests")
def test_smoke_generation():
    model = musicgen.MusicGen.get_pretrained("small")
    model.set_generation_params(duration=5)
    wav = model.generate(["creepy mechanical hallway"])
    audio_write("test_output", wav[0].cpu(), model.sample_rate)

