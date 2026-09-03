"""A reversible JaccardDrain template-mining playground for a Python console.

Usage:
    >>> from playground import TemplateMinerPlayground
    >>> miner = TemplateMinerPlayground()
    >>> miner.add("Order #100 confirmed for $7.20")
    >>> miner.clusters()
    >>> miner.undo()
    >>> miner.reset()
"""

from drain3.template_miner import TemplateMiner

from aggregator.template_mining import create_template_miner


class TemplateMinerPlayground:
    """Keep an in-memory JaccardDrain miner whose latest input can be undone."""

    def __init__(self) -> None:
        self.inputs: list[str] = []
        self._miner = self._new_miner()

    def add(self, message: str) -> dict[str, object]:
        """Add a message and return JaccardDrain's event plus current clusters."""
        result = self._miner.add_log_message(message)
        self.inputs.append(message)
        return {"event": result, "clusters": self.clusters()}

    def clusters(self) -> list[dict[str, object]]:
        """Return cluster IDs, sizes, and current mined templates."""
        return [
            {
                "id": cluster.cluster_id,
                "size": cluster.size,
                "template": cluster.get_template(),
            }
            for cluster in sorted(
                self._miner.drain.clusters,
                key=lambda cluster: cluster.cluster_id,
            )
        ]

    def undo(self) -> list[dict[str, object]] | bool:
        """Discard the last input and return the rebuilt clusters, or ``False``."""
        if not self.inputs:
            return False
        self.inputs.pop()
        self._rebuild()
        return self.clusters()

    def reset(self) -> None:
        """Clear all inputs and return to an empty miner."""
        self.inputs.clear()
        self._miner = self._new_miner()

    def _rebuild(self) -> None:
        self._miner = self._new_miner()
        for message in self.inputs:
            self._miner.add_log_message(message)

    @staticmethod
    def _new_miner() -> TemplateMiner:
        return create_template_miner()
