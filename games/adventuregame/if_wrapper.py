"""
    Module wrapping IF interpreter(s) for adventuregame.
"""


def split_state_string(state_string: str, value_delimiter: str = "(", value_separator: str = ","):
    """
    Split a state predicate string and return its values as a tuple.
    """
    first_split = state_string.split(value_delimiter, 1)
    predicate_type = first_split[0]
    if value_separator in first_split[1]:
        values_split = first_split[1][:-1].split(value_separator, 1)
        return predicate_type, values_split[0], values_split[1]
    else:
        return predicate_type, first_split[1][:-1]


class BasicIFInterpreter:
    """
    A basic/mock IF interpreter for prototyping adventuregame.
    """
    def __init__(self, game_instance: dict):
        self.game_instance: dict = game_instance

        self.world_state: set = set()
        self.goal_state: set = set()

        self.initialize_states_from_strings()

        # print("BasicIFInterpreter initialized:")
        # print("Game instance:", self.game_instance)
        print("Initial world state:", self.world_state)
        # print("Goal world state:", self.goal_state)

        # for state_pred in self.goal_state:
        #    print(self.split_state_string(state_pred))

        print(self.get_full_room_desc())

    def initialize_states_from_strings(self):
        """
        Convert List[Str] world state format into Set[Tuple].
        """
        for state_string in self.game_instance['initial_state']:
            self.world_state.add(split_state_string(state_string))
        for state_string in self.game_instance['goal_state']:
            self.goal_state.add(split_state_string(state_string))

    def get_full_room_desc(self):
        """
        Full description of the room the player is at.
        """
        # get player room:
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[2] == 'player':
                player_room = state_pred[1]
        # create room description start:
        player_at_str = f"You are in the {player_room}."
        # get player room contents:
        room_contents = list()
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[1] == player_room and not state_pred[2] == 'player':
                room_contents.append(state_pred[2])
        print("Room contents:", room_contents)
        # check room content visibility:
        visible_contents = list()
        for thing in room_contents:
            print(f"Checking {thing}...")
            contained_in = None
            for state_pred in self.world_state:
                if state_pred[0] == 'in' and state_pred[2] == thing:
                    print(f"'in' predicate found:", state_pred)
                    contained_in = state_pred[1]
                    print(f"{thing} contained in {contained_in}")
                    for state_pred2 in self.world_state:
                        if state_pred2[0] == 'closed' and state_pred2[1] == contained_in:
                            # not visible in closed container
                            print(f"{contained_in} containing {thing} is closed.")
                            break
                        elif state_pred2[0] == 'open' and state_pred2[1] == contained_in:
                            visible_contents.append(thing)
                            break
            if contained_in:
                continue
            print(f"{thing} not contained in anything.")
            visible_contents.append(thing)

        print("Visible contents:", visible_contents)
        # create visible room content description:
        visible_contents_str = str()
        if len(visible_contents) >= 3:
            comma_list = ", a ".join(visible_contents[:-1])
            and_last = f"and a {visible_contents[-1]}"
            visible_contents_str = f"There are a {comma_list} {and_last}."
        elif len(visible_contents) == 2:
            visible_contents_str = f"There are a {visible_contents[0]} and a {visible_contents[1]}."
        elif len(visible_contents) == 1:
            visible_contents_str = f"There is a {visible_contents[0]}."
        # get predicate states of visible objects and create textual representations:
        visible_content_state_strs = list()
        for thing in visible_contents:
            for state_pred in self.world_state:
                if state_pred[0] == 'closed' and state_pred[1] == thing:
                    visible_content_state_strs.append(f"The {thing} is closed.")
                elif state_pred[0] == 'open' and state_pred[1] == thing:
                    visible_content_state_strs.append(f"The {thing} is open.")
                if state_pred[0] == 'in' and state_pred[2] == thing:
                    visible_content_state_strs.append(f"The {thing} is in the {state_pred[1]}.")
                if state_pred[0] == 'on' and state_pred[2] == thing:
                    visible_content_state_strs.append(f"The {thing} is on the {state_pred[1]}.")
        visible_content_state_combined = " ".join(visible_content_state_strs)
        # combine full room description:
        room_description = f"{player_at_str} {visible_contents_str} {visible_content_state_combined}"

        return room_description
