from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from drain3.jaccard_drain import JaccardDrain

_PLAYGROUND_PATH = Path(__file__).parents[1] / "playground.py"
_SPEC = spec_from_file_location("playground", _PLAYGROUND_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_PLAYGROUND_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PLAYGROUND_MODULE)
TemplateMinerPlayground = _PLAYGROUND_MODULE.TemplateMinerPlayground


def test_playground_uses_jaccard_drain_when_created_reset_and_rebuilt() -> None:
    playground = TemplateMinerPlayground()
    initial_miner = playground._miner

    assert isinstance(initial_miner.drain, JaccardDrain)
    assert playground.add("Order #100 confirmed") == {
        "event": {
            "change_type": "cluster_created",
            "cluster_id": 1,
            "cluster_size": 1,
            "template_mined": "Order #<NUMBER> confirmed",
            "cluster_count": 1,
        },
        "clusters": [{"id": 1, "size": 1, "template": "Order #<NUMBER> confirmed"}],
    }

    playground.reset()

    assert playground.inputs == []
    assert playground._miner is not initial_miner
    assert isinstance(playground._miner.drain, JaccardDrain)

    playground.add("Order #100 confirmed")
    playground.add("Order #101 confirmed")
    miner_before_undo = playground._miner

    assert playground.undo() == [{"id": 1, "size": 1, "template": "Order #<NUMBER> confirmed"}]
    assert playground._miner is not miner_before_undo
    assert isinstance(playground._miner.drain, JaccardDrain)
