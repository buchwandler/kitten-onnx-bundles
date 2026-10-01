# OnnxVoice integration brief

## Parser

Add `onnxvoice/catalog_tools/kitten.py` plus a `_parse_kitten()` hook (or preferably a generic
system descriptor registry).

The catalog schema maps directly to `CatalogItem`:

```text
system          = kitten
id              = model.id
kind            = model
sample_rate     = model.sample_rate
voices          = voice_aliases.keys()
artifact role   = model | voices
artifact quality= model.quality when useful
metadata        = language, quality, runtime, upstream, voice_aliases, speed_priors, metadata
```

Alias resolution should be case-sensitive initially because the upstream model IDs are simple and
stable.

## Runtime adapter

Add:

```text
onnxvoice/systems/kitten.py
tests/test_kitten_contract.py
tests/test_kitten_adapter.py
tests/test_kitten_catalog.py
tests/test_kitten_local_open.py
docs/systems/kitten.md
```

Minimal API:

```python
runtime.infer(token_ids, style=style, speed=1.0)
```

Expected Kitten v0.8 graph semantic inputs:

```text
input_ids
style
speed
```

Do not have the adapter phonemize raw text. KittenSynth owns text -> token IDs and voice-style
selection.

The adapter should inspect graph input specs at runtime instead of trusting filenames, validate
dtype/rank, run the model, reproduce upstream output-tail handling for parity, and return canonical
mono finite float32 audio at 24 kHz.

## Local open

The existing API is already sufficient once the adapter is registered:

```python
onnxvoice.open_local(
    system="kitten",
    model="kitten_tts_nano_v0_8.onnx",
    voices="voices.npz",
    metadata={
        "runtime": {"profile": "ONNX2"},
        "voice_aliases": {...},
        "speed_priors": {...},
    },
    sample_rate=24000,
)
```

The Kitten adapter only needs the `model` artifact for inference when KittenSynth supplies `style`
explicitly. Keeping `voices` in the installation is still useful for integrity/provenance and
higher-level clients.
