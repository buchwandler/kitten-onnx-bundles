# kitten-onnx-bundles

A small, reproducible catalog of upstream KittenTTS ONNX model bundles for consumers such as
OnnxVoice and KittenSynth.

## What this repository is

- Normalized KittenTTS model metadata.
- Exact upstream repository/revision provenance.
- Revision-pinned artifact URLs.
- Positive artifact sizes and SHA-256 values.
- Stable voice aliases and speed-prior metadata extracted from upstream `config.json`.
- A JSON schema and deterministic local validation.
- **Not a model mirror.**

The upstream model files remain on Hugging Face. This repository only points to them.

## Why keep this separate?

KittenTTS currently publishes each v0.8 model variant as a small Hugging Face repository with an
ONNX file plus `voices.npz` and `config.json`. OnnxVoice could discover those repositories
directly, so a separate catalog is not technically mandatory.

It is still useful in the OnnxVoice architecture because it gives you a stable layer for:

- immutable revision pins instead of `main`;
- SHA-256/size integrity before installation;
- one normalized model ID independent of upstream repository names;
- voice/language/gender metadata for `onnxvoice list`;
- update checks without teaching the runtime about Hugging Face layout;
- future Kitten variants or community conversions without changing KittenSynth.

This mirrors the role of `pocket-onnx-bundles`, but is intentionally much smaller because Kitten
v0.8 is a two-runtime-artifact system rather than a multi-component graph bundle.

## Canonical files

```text
catalog/models.json
catalog/source.json
schemas/model-catalog.schema.json
```

## Bootstrap catalog

The MVP includes four current KittenML v0.8 repositories:

```text
kitten:nano-0.8-int8
kitten:nano-0.8-fp32
kitten:micro-0.8
kitten:mini-0.8
```

All produce 24 kHz English speech and use the current eight voice aliases.

`quality` is only asserted when it is explicit in the upstream repository name. `micro-0.8` and
`mini-0.8` therefore use `quality: null` in this bootstrap instead of guessing a precision label.

## Runtime artifacts

A model entry has exactly two installed runtime artifacts:

```text
role=model   -> *.onnx
role=voices  -> voices.npz
```

The upstream `config.json` is normalized into catalog metadata instead of being required at runtime.
Its important fields are:

```text
runtime.profile
voice_aliases
speed_priors
```

This avoids adding a third installed file that the ONNX adapter itself does not need.

## Consumer contract

OnnxVoice should parse this schema and emit a normal `CatalogItem`/`Installation`:

```python
installation = ov.install("kitten:nano-0.8-int8")
with ov.open(installation) as runtime:
    result = runtime.infer(token_ids, style=style, speed=1.0)
```

KittenSynth loads `voices.npz`, applies alias/style selection, and calls the tensor-level runtime.

See [`docs/onnxvoice-integration.md`](docs/onnxvoice-integration.md).

## Validate

```bash
python scripts/check_catalog.py
```

The validator checks:

- schema/kind
- globally unique model IDs and aliases
- exactly one `model` and one `voices` artifact per model
- immutable 40-character revision pins
- pinned Hugging Face resolve URLs
- positive sizes
- lowercase SHA-256 values
- 24 kHz positive sample rate
- voice alias integrity
- speed priors referring to known internal voices

## Refresh policy

The checked-in catalog is pinned data, not a model mirror or network crawler. Use OnnxVoice catalog tooling to refresh its upstream revisions and artifact metadata:

```bash
onnxvoice catalog kitten build \
  --seed-catalog catalog/models.json \
  --output catalog/models.json \
  --source-output catalog/source.json \
  --revision main
onnxvoice catalog kitten verify \
  --catalog catalog/models.json \
  --source catalog/source.json
```

The existing normalized catalog is the seed manifest for stable model IDs, aliases, language, quality, and upstream repositories. The builder resolves each listed repository to an immutable revision, reads its authoritative `config.json` and Hugging Face file metadata, and uses LFS size/SHA-256 values when available. It streams an artifact only when the repository does not expose usable integrity metadata. Output is deterministic for a fixed upstream revision. Build requires network access; verify is offline.

Review the catalog and source diffs before merging. The manual GitHub workflow runs this refresh and commits changed catalog files to the branch on which the workflow was dispatched.

## Licensing

Repository-authored metadata and scripts are Apache-2.0 in this MVP. Referenced KittenTTS v0.8
model repositories declare Apache-2.0 at the time of the snapshot. This repository does not
relicense or redistribute the model files.
