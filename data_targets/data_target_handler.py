from typing import Dict

from TiltHydrometer import TiltHydrometer

from .legacy_fermentrack_target import LegacyFermentrackTarget
from .bierbot_target import BierbotTarget

target_legacy_fermentrack = LegacyFermentrackTarget()
target_bierbottrack = BierbotTarget()


def process_data(tilts: Dict[str, TiltHydrometer]):
    # TODO - Make this asynchronous
    global target_legacy_fermentrack
    global target_bierbottrack

    target_legacy_fermentrack.process(tilts)
    target_bierbottrack.process(tilts)

def load_config():
    global target_legacy_fermentrack
    global target_bierbottrack

    target_legacy_fermentrack.load_config()
    target_bierbottrack.load_config()
