"""Read-only operator inspection surface. It cannot activate or call a provider."""

import argparse
import json
from importlib import resources
from .model_rotator import ProviderRegistryV1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adaptive-model-rotator")
    parser.add_argument("command", choices=("status",))
    parser.parse_args(argv)
    raw = json.loads(
        resources.files("adaptive_factory.resources").joinpath("model-rotator-registry.v1.json").read_text()
    )
    registry = ProviderRegistryV1.from_dict(raw)
    print(
        json.dumps(
            {
                "enabled": False,
                "live_qualification": "NOT_RUN",
                "registry_id": registry.registry_id,
                "registry_digest": registry.registry_digest,
                "candidate_count": len(registry.models),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0
