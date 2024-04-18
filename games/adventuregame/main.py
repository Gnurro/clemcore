from typing import List, Dict

from backends import Model
from clemgame import file_utils
from clemgame import metrics
from clemgame.clemgame import GameMaster, GameBenchmark, GameScorer, DialogueGameMaster
from clemgame import get_logger

import re

GAME_NAME = "adventuregame"
logger = get_logger(__name__)


class AdventureGameMaster(DialogueGameMaster):
    """
    DialogueGameMaster subclass for adventuregame.
    """
    def __init__(self, experiment: Dict, player_models: List[Model]):
        super().__init__(GAME_NAME, experiment, player_models)
        self.experiment = experiment
        self.game = None
        self.game_instance = None