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
        # create an experiment:
        experiment = self.add_experiment(f"basic_if")

        # load basic test adventures:
        adventures = self.load_json("resources/adventures")

        # Load the prepared initial prompt
        prompt = self.load_template("resources/initial_prompts/prompt")

        for adventure_id in tqdm(range(len(adventures))):
            goal_str = adventures[adventure_id]['goal']
            first_room_str = adventures[adventure_id]['first_room']

            # Replace the goal in the templated initial prompt
            instance_prompt = prompt.replace("$GOAL$", goal_str)
            instance_prompt = instance_prompt.replace("$FIRST_ROOM$", first_room_str)

            # Create a game instance
            game_instance = self.add_game_instance(experiment, adventure_id)
            game_instance["prompt"] = instance_prompt  # game parameters
            game_instance["goal_str"] = goal_str  # game parameters
            game_instance["first_room_str"] = first_room_str  # game parameters


if __name__ == '__main__':
    # The resulting instances.json is automatically saved to the "in" directory of the game folder
    AdventureGameInstanceGenerator().generate()