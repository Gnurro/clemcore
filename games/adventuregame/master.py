from typing import List, Dict, Tuple

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

        # check game variant:
        self.if_variant = self.game_instance['variant']

        # initialize IF interpreter:
        self.if_interpreter = BasicIFInterpreter(self.game_instance)

        # TODO: put all interpreter-relevant data into instances
        # TODO: use clemgame resource loading

        # create player:
        self.player = Player(self.player_models[0])

        # Add the players: these will be logged to the records interactions.json
        # Note: During game play the players will be called in the order added here
        self.add_player(self.player)

        # keep history of plans:
        if self.if_variant == 'plan':
            self.plan_history: list = list()

        self.goals_required = set(self.game_instance['goal_state'])
        self.goals_achieved = set()

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
        # Check responses for specific players
        if player == self.player:
            # Check rule: utterance starts with IF >
            if not utterance.startswith(">"):
                self.success = False
                return True
            if self.if_variant == 'plan':
                if "\nNext actions:" not in utterance:
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

    def _on_parse_response(self, player: Player, utterance: str) -> Tuple[str, bool]:
        """
        Hook

        Decide if a response utterance should be modified. If not simply return the utterance.

        When a modified utterance and a true value is returned, then a 'parse' event is logged.

        :param player: that produced the response
        :param utterance: to be potentially modified
        :return: the (modified) utterance and if to log the parse action (default: True)
        """
        if self.if_variant == 'plan':
            new_plan = utterance.split("\nNext actions:")[1]
            self.plan_history.append(new_plan)
            # print(self.plan_history)
            # TODO: set up limited plan feedback by removing plans here and feeding them back into messages by args

        return utterance, True

    def _does_game_proceed(self) -> bool:
        """
        Template method: must be implemented
        """
        # stop game when all goal states have been achieved:
        if self.goals_achieved == self.goals_required:
            return False
        # stop game when turn limit is reached:
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

        prior_goal_count = len(self.goals_achieved)

        goals_achieved, if_response = self.if_interpreter.process_action(if_input)
        self.goals_achieved = goals_achieved

        post_goal_count = len(self.goals_achieved)
        turn_score = post_goal_count - prior_goal_count
        print("turn score:", turn_score)

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
