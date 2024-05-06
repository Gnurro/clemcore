"""
    Module wrapping IF interpreter(s) for adventuregame.
"""

import json


PATH = "games/adventuregame/"


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

        self.entity_types = dict()
        self.initialize_entity_types()
        # print(self.entity_types)

        self.action_types = dict()
        self.initialize_action_types()
        # print(self.action_types)

        self.world_state: set = set()
        self.goal_state: set = set()

        self.initialize_states_from_strings()

        # print("BasicIFInterpreter initialized:")
        # print("Game instance:", self.game_instance)
        # print("Initial world state:", self.world_state)
        # print("Goal world state:", self.goal_state)

        # for state_pred in self.goal_state:
        #    print(self.split_state_string(state_pred))

        # print(self.get_full_room_desc())

    def initialize_entity_types(self):
        """
        Load and process entity types in this adventure.
        """
        # load basic entity types:
        with open(f"{PATH}resources/basic_entities.json", 'r', encoding='utf-8') as entities_file:
            entity_definitions = json.load(entities_file)
            for entity_definition in entity_definitions:
                self.entity_types[entity_definition['type_name']] = dict()
                for entity_attribute in entity_definition:
                    if not entity_attribute == 'type_name':
                        self.entity_types[entity_definition['type_name']][entity_attribute] = entity_definition[
                            entity_attribute]

    def initialize_action_types(self):
        """
        Load and process action types in this adventure.
        """
        # load basic action types:
        with open(f"{PATH}resources/basic_actions.json", 'r', encoding='utf-8') as actions_file:
            action_definitions = json.load(actions_file)
            for action_definition in action_definitions:
                self.action_types[action_definition['type_name']] = dict()
                for action_attribute in action_definition:
                    if not action_attribute == 'type_name':
                        self.action_types[action_definition['type_name']][action_attribute] = action_definition[
                            action_attribute]
        # for key, value in self.action_types.items():
        # print(self.action_types)
        for action_type in self.action_types:
            cur_action_type = self.action_types[action_type]
            # print(cur_action_type['object_post_state'])
            cur_action_type['object_post_state'] = split_state_string(cur_action_type['object_post_state'])

    def initialize_states_from_strings(self):
        """
        Convert List[Str] world state format into Set[Tuple].
        """
        for state_string in self.game_instance['initial_state']:
            self.world_state.add(split_state_string(state_string))

        preds_to_add = set()
        # add floors to rooms:
        for state_pred in self.world_state:
            if state_pred[0] == 'room':
                # print("room to add floor to found:", state_pred)
                preds_to_add.add(('at', 'floor', state_pred[1]))
                # print("pred to add:", preds_to_add)
        # put 'supported' items on the floor if they are not 'in' or 'on':
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and hasattr(self.entity_types[state_pred[1]], 'supported'):
                currently_supported = False
                for state_pred2 in self.world_state:
                    if state_pred2[0] == 'on' and state_pred2[2] == state_pred[1]:
                        currently_supported = True
                        break
                    if state_pred2[0] == 'in' and state_pred2[2] == state_pred[1]:
                        currently_supported = True
                        break
                if not currently_supported:
                    # self.world_state.add(('on', 'floor', state_pred[2]))
                    preds_to_add.add(('on', state_pred[1], 'floor'))

        self.world_state = self.world_state.union(preds_to_add)

        for state_string in self.game_instance['goal_state']:
            self.goal_state.add(split_state_string(state_string))

    def get_player_room(self):
        """
        Get the current room str.
        """
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[1] == 'player':
                player_room = state_pred[2]
        return player_room

    def get_player_room_contents(self):
        """
        Get all contents of the current room.
        """
        player_room = self.get_player_room()
        # print("player in room:", player_room)
        room_contents = list()
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[2] == player_room and not state_pred[1] == 'player':
                room_contents.append(state_pred[1])
        return room_contents

    def get_player_room_contents_visible(self):
        """
        Get the visible contents of the current room.
        """
        room_contents = self.get_player_room_contents()
        # print("player room contents:", room_contents)
        visible_contents = list()
        for thing in room_contents:
            # print(f"Checking {thing}...")
            contained_in = None
            for state_pred in self.world_state:
                # print("checking for visiblity:", state_pred)
                # check if entity is 'in' closed container:
                if state_pred[0] == 'in' and state_pred[1] == thing:
                    # print(f"'in' predicate found:", state_pred)
                    contained_in = state_pred[2]
                    # print(f"{thing} contained in {contained_in}")
                    for state_pred2 in self.world_state:
                        if state_pred2[0] == 'closed' and state_pred2[1] == contained_in:
                            # not visible in closed container
                            # print(f"{contained_in} containing {thing} is closed.")
                            break
                        elif state_pred2[0] == 'open' and state_pred2[1] == contained_in:
                            # print(f"the {state_pred2[1]} is {state_pred2[0]}")
                            visible_contents.append(thing)
                            break
                        elif state_pred2[1] == 'inventory' and state_pred2[1] == contained_in:
                            # TODO: figure out inventory item reporting
                            visible_contents.append(thing)
                            break
                if len(state_pred) >= 3 and state_pred[1] in self.entity_types:
                    if hasattr(self.entity_types[state_pred[1]], 'hidden'):
                        continue
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

    def get_inventory_content(self):
        """
        Get set of inventory content.
        """
        inventory_content = set()
        for state_pred in self.world_state:
            if state_pred[0] == 'in' and state_pred[2] == 'inventory':
                inventory_content.add(state_pred[1])
        return inventory_content

    def get_inventory_desc(self):
        """
        Get a text description of the inventory content.
        """
        inventory_content: set = self.get_inventory_content()
        inv_list = list(inventory_content)
        # print(inv_list)
        inv_item_cnt = len(inv_list)
        if inv_item_cnt == 0:
            inv_desc = "Your inventory is empty."
            return inv_desc
        elif inv_item_cnt == 1:
            inv_str = f"a {inv_list[0]}"
        else:
            inv_strs = [f"a {inv_item}" for inv_item in inv_list]
            # print(inv_strs)
            inv_str = ", ".join(inv_strs[:-1])
            inv_str += f" and {inv_strs[-1]}"
            # print(inv_str)
        inv_desc = f"In your inventory you have {inv_str}."
        # print(inv_desc)
        return inv_desc

    def parse_action_input(self, action_input: str):
        """
        Parse input action string to action tuple.
        Fail if action/entities are not registered.
        """
        # simple split for now:
        action_tuple = tuple(action_input.split())
        # assume VO:
        if action_tuple[0] not in self.action_types:
            return False, f"I don't know what '{action_tuple[0]}' means."
        if action_tuple[1] not in self.entity_types:
            return False, f"I don't know what a '{action_tuple[1]}' is."

        # TODO: handle (optional) transitive; 'take THING from OTHERTHING'

        # TODO: handle synonyms
        # TODO: handle split verbs

        return True, action_tuple

    def resolve_action(self, action_tuple: tuple):
        """
        Check action viability and change world state.
        """
        # print("action tuple:", action_tuple)
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
        pre_state_valence = len(object_pre_state)
        object_post_state = self.action_types[action_tuple[0]]['object_post_state']
        # print("object post state:", object_post_state)
        post_state_valence = len(object_post_state)
        # print("post state valence:", post_state_valence)

        # TODO: make predicates external to handle valence?

        state_changed = False


        if len(action_tuple) == 4 and action_tuple[0] == 'put':
            for state_pred in self.world_state:
                # print("checking state pred:", state_pred)
                if state_pred[0] in object_pre_state and state_pred[1] == action_tuple[1]:
                    # print("len 4 action:", state_pred, action_tuple)
                    self.world_state.remove(state_pred)

                    object_idx = object_post_state.index('THING')
                    # print("obj tuple idx:", object_idx)

                    target_idx = object_post_state.index('TARGET')
                    # print("target tuple idx:", target_idx)

                    new_pred = [object_post_state[0]]

                    if post_state_valence == 2:
                        new_pred.append(action_tuple[1])
                    elif post_state_valence == 3:
                        if object_idx == 1:
                            new_pred.append(action_tuple[1])
                        else:
                            # new_pred.append(object_post_state[1])
                            new_pred.append(action_tuple[3])
                        if object_idx == 2:
                            new_pred.append(action_tuple[1])
                        else:
                            new_pred.append(action_tuple[3])

                    new_predicate = tuple(new_pred)

                    # print("new predicate:", new_predicate)

                    self.world_state.add(new_predicate)
                    state_changed = True

        else:
            for state_pred in self.world_state:
                # print("checking state pred:", state_pred)
                if state_pred[0] in object_pre_state and state_pred[1] == action_tuple[1]:
                    # print(f"{state_pred} matches pre-state {object_pre_state} and {action_tuple[1]}")

                    self.world_state.remove(state_pred)
                    object_idx = object_post_state.index('THING')
                    # print("obj tuple idx:", object_idx)

                    new_pred = [object_post_state[0]]

                    if post_state_valence == 2:
                        new_pred.append(action_tuple[1])
                    elif post_state_valence == 3:
                        if object_idx == 1:
                            new_pred.append(action_tuple[1])
                        else:
                            new_pred.append(object_post_state[1])
                        if object_idx == 2:
                            new_pred.append(action_tuple[1])
                        else:
                            new_pred.append(object_post_state[2])

                    # new_predicate = (object_post_state, action_tuple[1])
                    new_predicate = tuple(new_pred)

                    self.world_state.add(new_predicate)
                    state_changed = True
                    break
                elif state_pred[0] in object_pre_state and state_pred[2] == action_tuple[1]:
                    # del state_pred
                    self.world_state.remove(state_pred)
                    object_idx = object_post_state.index('THING')
                    # print("obj tuple idx:", object_idx)

                    new_pred = [object_post_state[0]]

                    if post_state_valence == 2:
                        new_pred.append(action_tuple[1])
                    elif post_state_valence == 3:
                        if object_idx == 1:
                            new_pred.append(action_tuple[1])
                        else:
                            new_pred.append(object_post_state[1])
                        if object_idx == 2:
                            new_pred.append(action_tuple[1])
                        else:
                            new_pred.append(object_post_state[2])

                    # new_predicate = (object_post_state, action_tuple[1])
                    new_predicate = tuple(new_pred)

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
                print("resolution result:", resolution_result)
                if len(resolution_result) == 2:
                    base_result_str = f"The {resolution_result[1]} is now {resolution_result[0]}."
                elif len(resolution_result) == 3 and resolution_result[2] == 'inventory':
                    # handle taking/inventory:
                    base_result_str = f"You take the {resolution_result[1]}."
                    base_result_str += f" {self.get_inventory_desc()}"
                else:
                    base_result_str = (f"The {resolution_result[1]} is now {resolution_result[0]} "
                                       f"the {resolution_result[2]}.")

                # check for new visibles:
                post_visibles = set(self.get_player_room_contents_visible())
                # print("Post visibles:", post_visibles)
                # changed_visibles = prior_visibles.difference(post_visibles)
                changed_visibles = post_visibles.difference(prior_visibles)
                # print("Changed visibles:", changed_visibles)
                if changed_visibles:
                    # print("visibles changed!")
                    visible_content_state_strs = list()
                    for thing in changed_visibles:
                        for state_pred in self.world_state:
                            if state_pred[0] == 'in' and state_pred[1] == thing:
                                visible_content_state_strs.append(f"There is a {thing} in the {state_pred[2]}.")
                    visible_content_state_combined = " ".join(visible_content_state_strs)
                    print("New world state:", self.world_state)
                    return f"{base_result_str} {visible_content_state_combined}"
                else:
                    print("New world state:", self.world_state)
                    return base_result_str


if __name__ == "__main__":
    PATH = ""

    game_instance_exmpl = {"game_id": 0, "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "goal_str": "Put a sandwich on the table.", "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "initial_state": ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", "closed(refrigerator)", "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", "in(sandwich,refrigerator)"], "goal_state": ["on(sandwich,table)"]}

    # game_instance_exmpl = {"game_id": 0, "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "goal_str": "Put a sandwich on the table.", "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "initial_state": ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", "closed(refrigerator)", "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", "in(sandwich,refrigerator)", "in(pomegranate,inventory)"], "goal_state": ["on(sandwich,table)"]}
    # game_instance_exmpl = {"game_id": 0, "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "goal_str": "Put a sandwich on the table.", "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "initial_state": ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", "closed(refrigerator)", "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", "in(sandwich,refrigerator)", "in(pomegranate,inventory)", "in(yoyo,inventory)"], "goal_state": ["on(sandwich,table)"]}

    test_interpreter = BasicIFInterpreter(game_instance_exmpl)

    # print(test_interpreter.action_types)
    # print(test_interpreter.entity_types)

    turn_1 = test_interpreter.process_action("open refrigerator")
    print(turn_1)

    turn_2 = test_interpreter.process_action("take sandwich")
    print(turn_2)

    turn_3 = test_interpreter.process_action("put sandwich on table")
    print(turn_3)
