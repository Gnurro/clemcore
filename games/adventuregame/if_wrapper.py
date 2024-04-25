"""
    Module wrapping IF interpreter(s) for adventuregame.
"""

import json


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

        self.entity_types = dict()
        with open("games/adventuregame/resources/basic_entities.json", 'r', encoding='utf-8') as entities_file:
            entity_definitions = json.load(entities_file)
            for entity_definition in entity_definitions:
                self.entity_types[entity_definition['type_name']] = dict()
                for entity_attribute in entity_definition:
                    if not entity_attribute == 'type_name':
                        self.entity_types[entity_definition['type_name']][entity_attribute] = entity_definition[entity_attribute]
        # print(self.entity_types)

        self.action_types = dict()
        with open("games/adventuregame/resources/basic_actions.json", 'r', encoding='utf-8') as actions_file:
            action_definitions = json.load(actions_file)
            for action_definition in action_definitions:
                self.action_types[action_definition['type_name']] = dict()
                for action_attribute in action_definition:
                    if not action_attribute == 'type_name':
                        self.action_types[action_definition['type_name']][action_attribute] = action_definition[action_attribute]
        # print(self.action_types)

        # print("BasicIFInterpreter initialized:")
        # print("Game instance:", self.game_instance)
        # print("Initial world state:", self.world_state)
        # print("Goal world state:", self.goal_state)

        # for state_pred in self.goal_state:
        #    print(self.split_state_string(state_pred))

        # print(self.get_full_room_desc())

    def initialize_states_from_strings(self):
        """
        Convert List[Str] world state format into Set[Tuple].
        """
        for state_string in self.game_instance['initial_state']:
            self.world_state.add(split_state_string(state_string))
        for state_string in self.game_instance['goal_state']:
            self.goal_state.add(split_state_string(state_string))

    def get_player_room(self):
        """
        Get the current room str.
        """
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[2] == 'player':
                player_room = state_pred[1]
        return player_room

    def get_player_room_contents(self):
        """
        Get all contents of the current room.
        """
        player_room = self.get_player_room()
        room_contents = list()
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[1] == player_room and not state_pred[2] == 'player':
                room_contents.append(state_pred[2])
        return room_contents

    def get_player_room_contents_visible(self):
        """
        Get the visible contents of the current room.
        """
        room_contents = self.get_player_room_contents()
        visible_contents = list()
        for thing in room_contents:
            # print(f"Checking {thing}...")
            contained_in = None
            for state_pred in self.world_state:
                if state_pred[0] == 'in' and state_pred[2] == thing:
                    # print(f"'in' predicate found:", state_pred)
                    contained_in = state_pred[1]
                    # print(f"{thing} contained in {contained_in}")
                    for state_pred2 in self.world_state:
                        if state_pred2[0] == 'closed' and state_pred2[1] == contained_in:
                            # not visible in closed container
                            # print(f"{contained_in} containing {thing} is closed.")
                            break
                        elif state_pred2[0] == 'open' and state_pred2[1] == contained_in:
                            visible_contents.append(thing)
                            break
            if contained_in:
                continue
            # print(f"{thing} not contained in anything.")
            visible_contents.append(thing)
        return visible_contents

    def get_full_room_desc(self):
        """
        Full description of the room the player is at.
        Handles entity visibility inside closed/open containers.
        """
        # get player room:
        player_room = self.get_player_room()
        # create room description start:
        player_at_str = f"You are in the {player_room}."

        # get visible room content:
        visible_contents = self.get_player_room_contents_visible()

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

    def parse_action_input(self, action_input: str):
        """
        Parse input action string to action tuple.
        Fail if action/entities are not registered.
        """
        # simple split for now:
        action_tuple = action_input.split()
        # assume VO:
        if action_tuple[0] not in self.action_types:
            return False, f"I don't know what '{action_tuple[0]}' means."
        if action_tuple[1] not in self.entity_types:
            return False, f"I don't know what a '{action_tuple[1]}' is."

        return True, action_tuple

    def resolve_action(self, action_tuple: tuple):
        """
        Check action viability and change world state.
        """
        # check general action-object compatibility:
        compatible = False
        object_req_attribute = self.action_types[action_tuple[0]]['object_req_attribute']
        if object_req_attribute in self.entity_types[action_tuple[1]]:
            if self.entity_types[action_tuple[1]][object_req_attribute]:
                compatible = True
        if not compatible:
            return False, f"{action_tuple[1]} is not {object_req_attribute}"
        # check object pre state:
        object_pre_state = self.action_types[action_tuple[0]]['object_pre_state']
        object_post_state = self.action_types[action_tuple[0]]['object_post_state']
        state_changed = False
        for state_pred in self.world_state:
            if state_pred[0] == object_pre_state and state_pred[1] == action_tuple[1]:
                # del state_pred
                self.world_state.remove(state_pred)
                new_predicate = (object_post_state, action_tuple[1])
                self.world_state.add(new_predicate)
                state_changed = True
                break
        if state_changed:
            return True, new_predicate
        else:
            return False, f"{action_tuple[1]} is not {object_pre_state}"

    def process_action(self, action_input: str):
        """
        Fully process an action input.
        """
        print("Old world state:", self.world_state)
        parsed, parse_result = self.parse_action_input(action_input)
        if not parsed:
            return parse_result
        else:
            prior_visibles = set(self.get_player_room_contents_visible())
            # print("Prior visibles:", prior_visibles)
            resolved, resolution_result = self.resolve_action(parse_result)
            if not resolved:
                return resolution_result
            else:
                base_result_str = f"The {resolution_result[1]} is now {resolution_result[0]}."
                # check for new visibles:
                post_visibles = set(self.get_player_room_contents_visible())
                # print("Post visibles:", post_visibles)
                # changed_visibles = prior_visibles.difference(post_visibles)
                changed_visibles = post_visibles.difference(prior_visibles)
                # print("Changed visibles:", changed_visibles)
                if changed_visibles:
                    visible_content_state_strs = list()
                    for thing in changed_visibles:
                        for state_pred in self.world_state:
                            if state_pred[0] == 'in' and state_pred[2] == thing:
                                visible_content_state_strs.append(f"There is a {thing} in the {state_pred[1]}.")
                    visible_content_state_combined = " ".join(visible_content_state_strs)
                    print("New world state:", self.world_state)
                    return f"{base_result_str} {visible_content_state_combined}"
                else:
                    print("New world state:", self.world_state)
                    return base_result_str