#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "catalog" / "models.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the committed Kitten ONNX catalog")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    errors: list[str] = []

    if catalog.get("schema") != 1:
        errors.append("schema must be 1")
    if catalog.get("kind") != "kitten-onnx-model-catalog":
        errors.append("kind must be kitten-onnx-model-catalog")

    models = catalog.get("models")
    if not isinstance(models, dict) or not models:
        errors.append("models must be a non-empty object")
        models = {}

    identifiers: dict[str, str] = {}
    artifact_count = 0

    for key, model in models.items():
        label = f"models.{key}"
        if not SAFE_RE.fullmatch(key):
            errors.append(f"{label}: unsafe model key")
        if model.get("id") != key:
            errors.append(f"{label}: id must equal object key")

        for name in [key, *model.get("aliases", [])]:
            previous = identifiers.get(name)
            if previous is not None:
                errors.append(f"{label}: identifier {name!r} already used by {previous}")
            else:
                identifiers[name] = key

        sample_rate = model.get("sample_rate")
        if not isinstance(sample_rate, int) or isinstance(sample_rate, bool) or sample_rate <= 0:
            errors.append(f"{label}: sample_rate must be a positive integer")

        upstream = model.get("upstream") or {}
        repository = upstream.get("repository")
        revision = upstream.get("revision")
        if not isinstance(repository, str) or repository.count("/") != 1:
            errors.append(f"{label}: invalid upstream repository")
        if not isinstance(revision, str) or REVISION_RE.fullmatch(revision) is None:
            errors.append(f"{label}: upstream revision must be a 40-char lowercase SHA")

        artifacts = model.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append(f"{label}: artifacts must be a list")
            artifacts = []

        roles = [artifact.get("role") for artifact in artifacts if isinstance(artifact, dict)]
        if sorted(roles) != ["model", "voices"]:
            errors.append(f"{label}: expected exactly model and voices artifact roles")

        for index, artifact in enumerate(artifacts):
            artifact_count += 1
            alabel = f"{label}.artifacts[{index}]"
            if not isinstance(artifact, dict):
                errors.append(f"{alabel}: artifact must be an object")
                continue
            size = artifact.get("size")
            digest = artifact.get("sha256")
            url = artifact.get("url")
            filename = artifact.get("filename")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                errors.append(f"{alabel}: size must be positive")
            if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                errors.append(f"{alabel}: sha256 must be lowercase 64-char hex")
            if not isinstance(filename, str) or SAFE_RE.fullmatch(filename) is None:
                errors.append(f"{alabel}: unsafe filename")
            if isinstance(repository, str) and isinstance(revision, str) and isinstance(filename, str):
                expected_prefix = f"https://huggingface.co/{repository}/resolve/{revision}/"
                if not isinstance(url, str) or not url.startswith(expected_prefix):
                    errors.append(f"{alabel}: URL is not pinned to model upstream revision")

        aliases = model.get("voice_aliases")
        if not isinstance(aliases, dict) or not aliases:
            errors.append(f"{label}: voice_aliases must be a non-empty object")
            internal_voices: set[str] = set()
        else:
            internal_voices = {str(value) for value in aliases.values()}
            if len(internal_voices) != len(aliases):
                errors.append(f"{label}: voice aliases must map one-to-one in the bootstrap catalog")
            for display, internal in aliases.items():
                if not isinstance(display, str) or not display:
                    errors.append(f"{label}: empty voice alias")
                if not isinstance(internal, str) or SAFE_RE.fullmatch(internal) is None:
                    errors.append(f"{label}: unsafe internal voice id {internal!r}")

        priors = model.get("speed_priors")
        if not isinstance(priors, dict):
            errors.append(f"{label}: speed_priors must be an object")
        else:
            for voice_id, value in priors.items():
                if voice_id not in internal_voices:
                    errors.append(f"{label}: speed prior refers to unknown voice {voice_id!r}")
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    errors.append(f"{label}: invalid speed prior for {voice_id!r}")

    if errors:
        print("Kitten catalog validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Kitten catalog validation passed: models={len(models)} "
        f"identifiers={len(identifiers)} artifacts={artifact_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
