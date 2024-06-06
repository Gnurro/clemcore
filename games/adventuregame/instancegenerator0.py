"""
Generate instances for adventuregame.

Creates files in ./in
"""
from tqdm import tqdm

import clemgame
from clemgame.clemgame import GameInstanceGenerator

logger = clemgame.get_logger(__name__)

GAME_NAME = "adventuregame"


class AdventureGameInstanceGenerator(GameInstanceGenerator):
    def __init__(self):
        super().__init__(GAME_NAME)

    def on_generate(self):
        # load basic test adventures:
        adventures = self.load_json("resources/adventures")

        # BASIC IF

        # create an experiment:
        basic_experiment = self.add_experiment(f"basic_if")

        # TODO: goal state to text?

        # Load the prepared initial prompt
        basic_prompt = self.load_template("resources/initial_prompts/basic_prompt")

        for adventure_id in tqdm(range(len(adventures))):
            goal_str = adventures[adventure_id]['goal']
            first_room_str = adventures[adventure_id]['first_room']

            initial_state = adventures[adventure_id]['initial_state']
            goal_state = adventures[adventure_id]['goal_state']

            # Replace the goal in the templated initial prompt
            instance_prompt = basic_prompt.replace("$GOAL$", goal_str)
            # instance_prompt = instance_prompt.replace("$FIRST_ROOM$", first_room_str)

            # Create a game instance
            game_instance = self.add_game_instance(basic_experiment, adventure_id)
            game_instance["variant"] = "basic"  # game parameters
            game_instance["prompt"] = instance_prompt  # game parameters
            game_instance["goal_str"] = goal_str  # game parameters
            game_instance["first_room_str"] = first_room_str  # game parameters
            game_instance["initial_state"] = initial_state  # game parameters
            game_instance["goal_state"] = goal_state  # game parameters
            game_instance["max_turns"] = adventures[adventure_id]['max_turns']  # game parameters

        # PLANNING

        # create an experiment:
        planning_experiment = self.add_experiment(f"planning_if")

        # Load the prepared initial prompt
        planning_prompt = self.load_template("resources/initial_prompts/plan_prompt")

        for adventure_id in tqdm(range(len(adventures))):
            goal_str = adventures[adventure_id]['goal']
            first_room_str = adventures[adventure_id]['first_room']

            initial_state = adventures[adventure_id]['initial_state']
            goal_state = adventures[adventure_id]['goal_state']

            # Replace the goal in the templated initial prompt
            instance_prompt = planning_prompt.replace("$GOAL$", goal_str)
            # instance_prompt = instance_prompt.replace("$FIRST_ROOM$", first_room_str)

            # Create a game instance
            game_instance = self.add_game_instance(planning_experiment, adventure_id)
            game_instance["variant"] = "plan"  # game parameters
            # TODO: add parameter for plan retention
            game_instance["prompt"] = instance_prompt  # game parameters
            game_instance["goal_str"] = goal_str  # game parameters
            game_instance["first_room_str"] = first_room_str  # game parameters
            game_instance["initial_state"] = initial_state  # game parameters
            game_instance["goal_state"] = goal_state  # game parameters
            game_instance["max_turns"] = adventures[adventure_id]['max_turns']  # game parameters


if __name__ == '__main__':
    # The resulting instances.json is automatically saved to the "in" directory of the game folder
    AdventureGameInstanceGenerator().generate()