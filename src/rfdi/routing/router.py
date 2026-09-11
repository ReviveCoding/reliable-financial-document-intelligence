from enum import Enum


class Action(str, Enum):
    AUTO_ACCEPT = "AUTO_ACCEPT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK_OR_QUARANTINE = "BLOCK_OR_QUARANTINE"


def route(risk: float, *, schema_valid: bool, attack_signal: bool = False,
          review_threshold: float = 0.36, quarantine_threshold: float = 0.78) -> Action:
    if not schema_valid or attack_signal or risk >= quarantine_threshold:
        return Action.BLOCK_OR_QUARANTINE
    if risk >= review_threshold:
        return Action.HUMAN_REVIEW
    return Action.AUTO_ACCEPT
