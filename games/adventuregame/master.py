from typing import List, Dict

from backends import Model
from clemgame import file_utils
from clemgame import metrics
from clemgame.clemgame import GameMaster, GameBenchmark, GameScorer, DialogueGameMaster, Player
from clemgame import get_logger

from games.adventuregame.if_wrapper import BasicIFInterpreter

import re

GAME_NAME = "adventuregame"
logger = get_logger(__name__)


class AdventureGameMaster(DialogueGameMaster):
    """
    DialogueGameMaster subclass for adventuregame.
    """
    def __init__(self, experiment: Dict, player_models: List[Model]):
        super().__init__(GAME_NAME, experiment, player_models)
        # self.experiment = experiment
        # self.game = None
        # self.game_instance = None
        self.turns = []
        self.success = True

    def _on_setup(self, **game_instance):
        self.game_instance = game_instance  # fetch game parameters here

        # print("game_instance type:", type(game_instance))

        # initialize IF interpreter:
        self.if_interpreter = BasicIFInterpreter(self.game_instance)

        # TODO: put all interpreter-relevant data into instances
        # TODO: use clemgame resource loading

        # create player:
        self.player = Player(self.player_models[0])

        # Add the players: these will be logged to the records interactions.json
        # Note: During game play the players will be called in the order added here
        self.add_player(self.player)

    def _on_before_game(self):
        # get initial room description from IF interpreter:
        initial_room_desc = self.if_interpreter.get_full_room_desc()

        first_message = self.game_instance["prompt"] + initial_room_desc

        # Do something before the game start e.g. add the initial prompts to the message list for the players
        # self.add_user_message(self.player, self.game_instance["prompt"])
        self.add_user_message(self.player, first_message)

        # print(self.messages_by_names[self.player.descriptor])
        # print(self.get_players())

    def _validate_player_response(self, player: Player, utterance: str) -> bool:
        # TODO: hook in and separate plans from IF inputs to allow different levels of feeding plans back into context
        # Check responses for specific players
        if player == self.player:
            # TODO: check for plan tag for planning version
            # Check rule: utterance starts with IF >
            if not utterance.startswith(">"):
                self.success = False
                return True
            """
            # Check rule: required words are included
            utterance = utterance.lower()
            utterance = utterance.translate(str.maketrans("", "", string.punctuation))
            for required_word in self.required_words:
                if required_word not in utterance:
                    self.success = False
            """
        return True

    def _does_game_proceed(self) -> bool:
        """
        Template method: must be implemented
        """
        # raise NotImplementedError()
        if len(self.turns) >= 5:
            return False
        return True

    def _on_after_turn(self, turn_idx: int):
        """
        Play loop hook: Called after all players have been prompted and their responses have been parsed+validated.
        """
        # print("_on_after_turn call starts")
        # IF INTERACTION
        # get the last player action:
        # print("Player messages:", self.messages_by_names[self.player.descriptor])
        last_action: str = self.messages_by_names[self.player.descriptor][-1]['content']
        # print("Last player message:", last_action)
        # strip player action to IF input:
        # if_input: str = last_action[1:].strip()
        if_input: str = last_action[1:].split("\n")[0].strip()
        # print("Stripped IF input:", if_input)

        goals_achieved, if_response = self.if_interpreter.process_action(if_input)
        self.add_user_message(self.player, if_response)

        # record successful turn:
        self.turns.append(self.success)

        # print("_on_after_turn call ends")


class AdventureGameScorer(GameScorer):
    def __init__(self, name: str, experiment: Dict, game_instance: Dict):
        super().__init__(name, experiment, game_instance)


class AdventureGameBenchmark(GameBenchmark):
    def __init__(self):
        super().__init__(GAME_NAME)

    def get_description(self):
        return "Text adventure game"

    def create_game_master(self, experiment: Dict, player_models: List[Model]) -> GameMaster:
        return AdventureGameMaster(experiment, player_models)

    def create_game_scorer(self, experiment: Dict, game_instance: Dict) -> GameScorer:
        return AdventureGameScorer(GAME_NAME, experiment, game_instance)
