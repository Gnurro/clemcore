"""
    IF interpreter for adventuregame.
"""

import json
import lark
from lark import Lark, Transformer
import jinja2
import os
from copy import deepcopy

from clemgame.clemgame import GameResourceLocator

from games.adventuregame.adv_util import fact_str_to_tuple, fact_tuple_to_str

PATH = "games/adventuregame/"

RESOURCES_SUBPATH = "resources/"

GAME_NAME = "adventuregame"


class IFTransformer(Transformer):
    def action(self, content):
        action: lark.Tree = content[0]

        # print(action)

        action_type = action.data
        # print("action type:", action_type)

        action_content = action.children
        # print("action content:", action_content)

        action_dict = {'type': action_type.value}

        arguments = []

        arg_idx = 1

        for child in action_content:
            if type(child) == lark.Tree and child.data == 'thing':
                # print("thing:", child.children)

                argument_words = [word.value for word in child.children if word.type == 'WORD']
                # print("argument words:", argument_words)

                arguments.append(" ".join(argument_words))

                # arguments.append(child.children[-1].value)
                # argument_adjs = [adj.value for adj in child.children[:-1] if adj.type == 'ADJ']
                argument_adjs = [adj.value.strip() for adj in child.children[:-1] if adj.type == 'ADJ']
                # print(argument_adjs)
                if argument_adjs:
                    action_dict[f'arg{arg_idx}_adjs'] = argument_adjs

                action_dict[f'arg{arg_idx}'] = arguments[-1]

                arg_idx += 1
            if type(child) == lark.Token and child.type == 'PREP':
                # action_dict['prep'] = child.value
                action_dict['prep'] = child.value.strip()
            if action_type.value == 'unknown' and type(child) == lark.Token and child.type == 'WORD':
                action_dict[f'arg{arg_idx}'] = child.value
                break

        # TODO: improve parsing feedback further

        return action_dict


class AdventureIFInterpreter(GameResourceLocator):
    """
    IF interpreter for adventuregame.
    """
    def __init__(self, game_instance: dict, name: str = GAME_NAME, verbose: bool = False):
        super().__init__(name)

        self.game_instance: dict = game_instance

        self.repr_str_to_type_dict: dict = dict()

        self.entity_types = dict()
        self.initialize_entity_types()
        # print(self.entity_types)

        self.room_types = dict()
        self.initialize_room_types()

        self.action_types = dict()
        self.initialize_action_types()
        # print(self.action_types)

        self.world_state: set = set()
        self.world_state_history: list = list()
        self.goal_state: set = set()
        self.goals_achieved: set = set()
        self.initialize_states_from_strings()

        self.initialize_action_parsing(print_lark_grammar=verbose)

        # print("BasicIFInterpreter initialized:")
        # print("Game instance:", self.game_instance)
        # print("Initial world state:", self.world_state)
        # print("Goal world state:", self.goal_state)

        # for state_pred in self.goal_state:
        #    print(self.fact_str_to_tuple(state_pred))

        # print(self.get_full_room_desc())

    def initialize_entity_types(self):
        """
        Load and process entity types in this adventure.
        """
        # load entity type definitions in game instance:
        entity_definitions: list = list()
        for entity_def_source in self.game_instance["entity_definitions"]:
            entities_file = self.load_json(f"resources{os.sep}definitions{os.sep}{entity_def_source[:-5]}")
            entity_definitions += entities_file

        for entity_definition in entity_definitions:
            self.entity_types[entity_definition['type_name']] = dict()
            for entity_attribute in entity_definition:
                if entity_attribute == 'type_name':
                    self.repr_str_to_type_dict[entity_definition['repr_str']] = entity_definition[entity_attribute]
                else:
                    self.entity_types[entity_definition['type_name']][entity_attribute] = entity_definition[
                        entity_attribute]

        # print(self.entity_types)

    def initialize_room_types(self):
        """
        Load and process room types in this adventure.
        """
        # load room type definitions in game instance:
        room_definitions: list = list()
        for room_def_source in self.game_instance["room_definitions"]:
            rooms_file = self.load_json(f"resources{os.sep}definitions{os.sep}{room_def_source[:-5]}")
            room_definitions += rooms_file

        for room_definition in room_definitions:
            self.room_types[room_definition['type_name']] = dict()
            for room_attribute in room_definition:
                if room_attribute == 'type_name':
                    self.repr_str_to_type_dict[room_definition['repr_str']] = room_definition[room_attribute]
                else:
                    self.room_types[room_definition['type_name']][room_attribute] = room_definition[
                        room_attribute]

        # print("repr to type:", self.repr_str_to_type_dict)

    def initialize_action_types(self):
        """
        Load and process action types in this adventure.
        """
        # load action type definitions in game instance:
        action_definitions: list = list()
        for action_def_source in self.game_instance["action_definitions"]:
            actions_file = self.load_json(f"resources{os.sep}definitions{os.sep}{action_def_source[:-5]}")
            action_definitions += actions_file

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
            cur_action_type['object_post_state'] = fact_str_to_tuple(cur_action_type['object_post_state'])

    def initialize_action_parsing(self, print_lark_grammar: bool = False):
        """
        Initialize the lark action input parser and transformer.
        """

        act_grammar_rules = list()
        act_grammar_larks = list()

        for action_type in self.action_types:
            cur_action_type = self.action_types[action_type]
            # print(cur_action_type['lark'])
            # action_lark: str = action_definition['lark']
            # print(action_lark)
            action_rule = cur_action_type['lark'].split(":")[0]
            # print(action_rule)
            act_grammar_rules.append(action_rule)
            act_grammar_larks.append(cur_action_type['lark'])

        act_grammar_action_line = f"action: {' | '.join(act_grammar_rules)} | unknown\n"
        # print(action_line)
        act_grammar_larks_str = "\n".join(act_grammar_larks)

        all_adjs = set()
        for entity_type, entity_def in self.entity_types.items():
            if 'possible_adjs' in entity_def:
                # print(entity_type)
                # print(entity_def['possible_adjs'])
                # print(entity_def.possible_adjs)
                new_adj_set = set(entity_def['possible_adjs'])
                all_adjs.update(new_adj_set)
        # print(all_adjs)
        all_adjs = [f'"{adj}"' for adj in all_adjs]

        act_grammar_adj_line = f"ADJ.1: ({' | '.join(all_adjs)}) WS\n"

        # print(act_grammar_adj_line)

        grammar_core = self.load_json(f"resources{os.sep}grammar_core")
        grammar_head = grammar_core['grammar_head']
        grammar_foot = grammar_core['grammar_foot']
        """
        with open(f"{PATH}resources/grammar_core.json", 'r', encoding='utf-8') as grammar_core_file:
            grammar_core = json.load(grammar_core_file)
            grammar_head = grammar_core['grammar_head']
            grammar_foot = grammar_core['grammar_foot']
        """
        act_grammar = (f"{grammar_head}{act_grammar_action_line}"
                       f"{act_grammar_larks_str}\n{act_grammar_adj_line}{grammar_foot}")

        if print_lark_grammar:
            print(act_grammar)

        self.act_parser = Lark(act_grammar, start='action')
        self.act_transformer = IFTransformer()

    def initialize_states_from_strings(self):
        """
        Convert List[Str] world state format into Set[Tuple].
        """
        for fact_string in self.game_instance['initial_state']:
            self.world_state.add(fact_str_to_tuple(fact_string))

        # NOTE: The following world state augmentations are left in here to make manual adventure creation/modification
        # convenient. Initial adventure world states generated with the clingo adventure generator already cover these
        # augmentations.

        # print("unaugmented initial world:", self.world_state)

        facts_to_add = set()

        # add trait facts for objects:
        for fact in self.world_state:
            if fact[0] == 'type':
                # add trait facts by entity type:
                if 'traits' in self.entity_types[fact[2]]:
                    type_traits: list = self.entity_types[fact[2]]['traits']
                    for type_trait in type_traits:
                        facts_to_add.add((type_trait, fact[1]))
                """"""

        # add floors to rooms:
        for fact in self.world_state:
            if fact[0] == 'room':
                # print("room to add floor to found:", fact)
                facts_to_add.add(('type', f'{fact[1]}floor', 'floor'))
                facts_to_add.add(('at', f'{fact[1]}floor', fact[1]))
                # print("pred to add:", facts_to_add)

        self.world_state = self.world_state.union(facts_to_add)

        # get entity instance types from world state:
        self.inst_to_type_dict = dict()
        for fact in self.world_state:
            # entity instance to entity type mapping:
            if fact[0] == 'type':
                # print("type set:", fact)
                self.inst_to_type_dict[fact[1]] = fact[2]

        # get room instance types from world state:
        self.room_to_type_dict = dict()
        for fact in self.world_state:
            # room instance to room type mapping:
            if fact[0] == 'room':
                # print("type set:", fact)
                self.room_to_type_dict[fact[1]] = fact[2]

        # put 'supported' items on the floor if they are not 'in' or 'on':
        for fact in self.world_state:
            # print("checking", fact)
            if fact[1] in self.inst_to_type_dict:
                if self.inst_to_type_dict[fact[1]] in self.entity_types:
                    # print(self.entity_types[self.inst_to_type_dict[fact[1]]])
                    pass
            # if fact[0] == 'at' and hasattr(self.entity_types[self.inst_to_type_dict[fact[1]]], 'supported'):
            # if fact[0] == 'at' and 'supported' in self.entity_types[self.inst_to_type_dict[fact[1]]]:
            if fact[0] == 'at' and ('needs_support', fact[1]) in self.world_state:
                # print("needs support:", fact)
                currently_supported = False
                for state_pred2 in self.world_state:
                    if state_pred2[0] == 'on' and state_pred2[1] == fact[1]:
                        currently_supported = True
                        break
                    if state_pred2[0] == 'in' and state_pred2[1] == fact[1]:
                        currently_supported = True
                        break
                if not currently_supported:
                    # self.world_state.add(('on', 'floor', fact[2]))
                    # facts_to_add.add(('on', fact[1], 'floor'))
                    facts_to_add.add(('on', fact[1], f'{fact[2]}floor'))

        self.world_state = self.world_state.union(facts_to_add)
        # print("augmented initial world:", self.world_state)
        # add initial world state to world state history:
        self.world_state_history.append(deepcopy(self.world_state))

        for fact_string in self.game_instance['goal_state']:
            self.goal_state.add(fact_str_to_tuple(fact_string))

    def _get_inst_str(self, inst):
        """
        Get a full string representation of an entity instance with adjectives.
        """
        inst_adjs = list()
        # get adj preds:
        for fact in self.world_state:
            if fact[0] == 'adj' and fact[1] == inst:
                inst_adjs.append(fact[2])

        if inst in self.inst_to_type_dict:
            inst_type: str = self.inst_to_type_dict[inst]
        elif inst in self.room_to_type_dict:
            inst_type: str = self.room_to_type_dict[inst]

        if inst_type in self.entity_types:
            inst_str: str = self.entity_types[inst_type]['repr_str']
        elif inst_type in self.room_types:
            inst_str: str = self.room_types[inst_type]['repr_str']

        inst_adjs.append(inst_str)

        adj_str = " ".join(inst_adjs)

        # full_inst_str = f"{adj_str} {self.inst_to_type_dict[inst]}"
        # full_inst_str = f"{adj_str} {self.inst_to_type_dict[inst]}"

        # return full_inst_str
        return adj_str

    def get_player_room(self):
        """
        Get the current room str.
        """
        for fact in self.world_state:
            if fact[0] == 'at' and fact[1] == 'player1':
                player_room = fact[2]
                break
        return player_room

    def get_player_room_contents(self):
        """
        Get all contents of the current room.
        """
        player_room = self.get_player_room()
        # print("player in room:", player_room)
        room_contents = list()
        for fact in self.world_state:
            if fact[0] == 'at' and fact[2] == player_room and not fact[1] == 'player1':
                room_contents.append(fact[1])
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

            if 'hidden' in self.entity_types[self.inst_to_type_dict[thing]]:
                continue

            contained_in = None
            for fact in self.world_state:
                # print("checking for visiblity:", fact)
                # check if entity is 'in' closed container:
                if fact[0] == 'in' and fact[1] == thing:
                    # print(f"'in' predicate found:", fact)
                    contained_in = fact[2]
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
                            # TODO?: figure out inventory item reporting; handling in action resolve now
                            print("inventory?")
                            visible_contents.append(thing)
                            break
            if contained_in:
                continue
            # print(f"{thing} not contained in anything.")
            # print(f"appending {thing}\n")
            visible_contents.append(thing)
        return visible_contents

    def get_player_room_exits(self):
        """
        Get all exits of the current room.
        """
        player_room = self.get_player_room()
        # print("player in room:", player_room)
        room_exits = list()
        for fact in self.world_state:
            if fact[0] == 'exit' and fact[1] == player_room:
                room_exits.append(fact[2])
        return room_exits

    def get_full_room_desc(self):
        """
        Full description of the room the player is at.
        Handles entity visibility inside closed/open containers.
        """
        # get player room:
        player_room = self.get_player_room()
        # create room description start:
        room_repr_str = self.room_types[self.room_to_type_dict[player_room]]['repr_str']
        player_at_str = f"You are in a {room_repr_str} now."

        # get visible room content:
        internal_visible_contents = self.get_player_room_contents_visible()

        # convert to types:
        # print("visible contents:", internal_visible_contents)
        # visible_contents = [self.inst_to_type_dict[instance] for instance in internal_visible_contents]
        visible_contents = [self._get_inst_str(instance) for instance in internal_visible_contents]

        # print("visible contents:", visible_contents)

        # create visible room content description:
        visible_contents_str = str()
        if len(visible_contents) >= 3:
            comma_list = ", a ".join(visible_contents[:-1])
            and_last = f"and a {visible_contents[-1]}"
            visible_contents_str = f"There are a {comma_list} {and_last}."
            visible_contents_str = " " + visible_contents_str
        elif len(visible_contents) == 2:
            visible_contents_str = f"There are a {visible_contents[0]} and a {visible_contents[1]}."
            visible_contents_str = " " + visible_contents_str
        elif len(visible_contents) == 1:
            visible_contents_str = f"There is a {visible_contents[0]}."
            visible_contents_str = " " + visible_contents_str

        # get predicate states of visible objects and create textual representations:
        visible_content_state_strs = list()
        # for thing in visible_contents:
        for thing in internal_visible_contents:
            # print("visible thing:", thing)
            for fact in self.world_state:
                if fact[0] == 'closed' and fact[1] == thing:
                    # visible_content_state_strs.append(f"The {thing} is closed.")
                    visible_content_state_strs.append(f"The {self._get_inst_str(thing)} is closed.")
                elif fact[0] == 'open' and fact[1] == thing:
                    # visible_content_state_strs.append(f"The {thing} is open.")
                    visible_content_state_strs.append(f"The {self._get_inst_str(thing)} is open.")
                # if fact[0] == 'in' and fact[2] == thing:
                if fact[0] == 'in' and fact[1] == thing:
                    # print(f"The {thing} is in the {fact[2]}.")
                    # visible_content_state_strs.append(f"The {thing} is in the {fact[2]}.")
                    visible_content_state_strs.append(f"The {self._get_inst_str(thing)} is in the {self._get_inst_str(fact[2])}.")
                # if fact[0] == 'on' and fact[2] == thing:
                if fact[0] == 'on' and fact[1] == thing:
                    # print(f"The {thing} is on the {fact[2]}.")
                    # visible_content_state_strs.append(f"The {thing} is on the {fact[2]}.")
                    visible_content_state_strs.append(f"The {self._get_inst_str(thing)} is on the {self._get_inst_str(fact[2])}.")

        # TODO?: list multiple things in/on same container/support?

        if visible_content_state_strs:
            visible_content_state_combined = " ".join(visible_content_state_strs)
            visible_content_state_combined = " " + visible_content_state_combined
        else:
            visible_content_state_combined = str()

        # TODO: handle doors (once they exist); if they will exist...

        room_exits = self.get_player_room_exits()
        # print("room exits:", room_exits)
        """
        # convert target room IDs to type names:
        for target_room_idx, target_room in enumerate(room_exits):
            room_exits[target_room_idx] = self.room_to_type_dict[target_room]
        """
        exits_str = str()
        if len(room_exits) == 1:
            # exits_str = f" You can go to a {room_exits[0]} from here."
            # exits_str = f" There is a passage to a {room_exits[0]} here."
            exits_str = f" There is a passage to a {self._get_inst_str(room_exits[0])} here."
        elif len(room_exits) == 2:
            # exits_str = f" You can go to a {room_exits[0]} and a {room_exits[1]} from here."
            # exits_str = f" There are passages to a {room_exits[0]} and a {room_exits[1]} here."
            exits_str = f" There are passages to a {self._get_inst_str(room_exits[0])} and a {self._get_inst_str(room_exits[1])} here."
        elif len(room_exits) >= 3:
            comma_exits = ", a ".join([self._get_inst_str(room_exit) for room_exit in room_exits[:-1]])
            # exits_str = f" You can go to {comma_exits} and {room_exits[-1]} from here."
            # exits_str = f" There are passages to a {comma_exits} and a {room_exits[-1]} here."
            exits_str = f" There are passages to a {comma_exits} and a {self._get_inst_str(room_exits[-1])} here."

        # combine full room description:
        # room_description = f"{player_at_str} {visible_contents_str} {visible_content_state_combined} {exits_str}"
        room_description = f"{player_at_str}{visible_contents_str}{visible_content_state_combined}{exits_str}"
        # room_description = " ".join([player_at_str, visible_contents_str, visible_content_state_combined, exits_str])

        # return room_description
        return room_description

    def get_inventory_content(self):
        """
        Get set of inventory content.
        """
        inventory_content = set()
        for fact in self.world_state:
            if fact[0] == 'in' and fact[2] == 'inventory':
                inventory_content.add(fact[1])
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
            # inv_str = f"a {self.inst_to_type_dict[inv_list[0]]}"
            inv_str = f"a {self._get_inst_str(inv_list[0])}"
        else:
            # inv_strs = [f"a {self.inst_to_type_dict[inv_item]}" for inv_item in inv_list]
            inv_strs = [f"a {self._get_inst_str(inv_item)}" for inv_item in inv_list]
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
        # print("action input:", action_input)
        try:
            parsed_command = self.act_parser.parse(action_input)
        except Exception as exception:
            # print("lark exception:", exception)
            # fail_dict: dict = {'phase': "parsing", 'fail_type': "lark_exception", 'arg': exception}
            fail_dict: dict = {'phase': "parsing", 'fail_type': "lark_exception", 'arg': str(exception)}
            return False, f"I don't know what you mean.", fail_dict
        # print("parsed command:", parsed_command)
        action_dict = self.act_transformer.transform(parsed_command)
        # print("transformed action dict:", action_dict)

        # catch 'unknown' action parses:
        if action_dict['type'] == "unknown":
            if action_dict['arg1'] in self.action_types:
                # print("defined action verb, malformed command!")
                # TODO: log/score malformed commands properly
                # print("action_dict:", action_dict)
                fail_dict: dict = {'phase': "parsing", 'fail_type': "malformed_command", 'arg': str(action_dict)}
                return False, f"I don't know what you mean.", fail_dict

        if action_dict['type'] not in self.action_types:
            if 'arg1' in action_dict:
                fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_action_verb", 'arg': action_dict['arg1']}
                return False, f"I don't know what '{action_dict['arg1']}' means.", fail_dict
            else:
                fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_action", 'arg': action_input}
                return False, f"I don't know what you mean.", fail_dict

        """"""
        if action_dict['arg1'] in self.repr_str_to_type_dict:
            # convert arg1 from repr to internal type:
            action_dict['arg1'] = self.repr_str_to_type_dict[action_dict['arg1']]
            # TODO: check if this conversion might be better elsewhere
        else:
            # TODO: if arg not in repr_str dict, it's already undefined -> refactor
            fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_repr_str", 'arg': action_dict['arg1']}
            return False, f"I don't know what '{action_dict['arg1']}' means.", fail_dict
        """
        if 'arg2' in action_dict:
            if action_dict['arg2'] in self.repr_str_to_type_dict:
                # convert arg1 from repr to internal type:
                action_dict['arg2'] = self.repr_str_to_type_dict[action_dict['arg2']]
                # TODO: check if this conversion might be better elsewhere
            else:
                # TODO: if arg not in repr_str dict, it's already undefined -> refactor
                fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_repr_str", 'arg': action_dict['arg2']}
                return False, f"I don't know what '{action_dict['arg2']}' means.", fail_dict
        """

        """
        if self.repr_str_to_type_dict[action_dict['arg1']] not in self.entity_types:
            if self.repr_str_to_type_dict[action_dict['arg1']] not in self.room_types:
                return False, f"I don't know what a '{action_dict['arg1']}' is."
        """
        if action_dict['arg1'] not in self.entity_types:
            if action_dict['arg1'] not in self.room_types:
                fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_type", 'arg': action_dict['arg1']}
                return False, f"I don't know what a '{action_dict['arg1']}' is.", fail_dict

        if 'arg2' in action_dict:
            if action_dict['type'] == "take":
                if action_dict['arg2'] == "inventory":
                    # print("taking from inventory")
                    fail_dict: dict = {'phase': "parsing", 'fail_type': "taking_from_inventory", 'arg': action_dict['arg2']}
                    # TODO: improve response text
                    return False, f"Things in your inventory are already taken.", fail_dict
            if action_dict['arg2'] in self.repr_str_to_type_dict:
                # convert arg1 from repr to internal type:
                action_dict['arg2'] = self.repr_str_to_type_dict[action_dict['arg2']]
                if action_dict['arg2'] in self.room_types:
                    cur_room_str = self.room_types[self.room_to_type_dict[self.get_player_room()]]['repr_str']
                    if not action_dict['arg2'] == cur_room_str:
                        fail_dict: dict = {'phase': "parsing", 'fail_type': "other_room_argument",
                                           'arg': action_dict['arg2']}
                        return False, f"You are not in a {action_dict['arg2']}.", fail_dict
                """
                elif action_dict['arg2'] not in self.entity_types:
                    fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_type", 'arg': action_dict['arg2']}
                    return False, f"I don't know what a '{action_dict['arg2']}' is.", fail_dict
                """
            else:
                fail_dict: dict = {'phase': "parsing", 'fail_type': "undefined_repr_str", 'arg': action_dict['arg2']}
                return False, f"I don't know what '{action_dict['arg2']}' means.", fail_dict

        # print("known type checks passed")

        return True, action_dict, {}

    def resolve_action(self, action_dict: dict):
        """
        Check action viability and change world state.
        """
        # print("action dict:", action_dict)

        # get state changes for current action:
        state_changes = self.action_types[action_dict['type']]['state_changes']
        # print("current action state changes:", state_changes)
        state_changed = False
        facts_to_remove = list()
        facts_to_add = list()
        for state_change in state_changes:
            # NOTE: only resolve if all state changes go through
            # print("\ncurrent state change:", state_change)

            # GO ACTION/ROOM TRAVERSAL
            if "HERE" in state_change['pre_state'] or "HERE" in state_change['post_state']:

                # check if arg is a room type:
                if action_dict['arg1'] not in self.room_types:
                    fail_dict: dict = {'phase': "resolution", 'fail_type': "not_room_type", 'arg': action_dict['arg1']}
                    not_room_type_str: str = f"I don't know what room '{action_dict['arg1']}' is."
                    return False, not_room_type_str, fail_dict

                # get things here:
                things_here = set(self.get_player_room_contents_visible()) | self.get_inventory_content()

                # print("HERE found in", state_change)
                present_exits = self.get_player_room_exits()
                # print("present exits:", present_exits)
                # TODO: check exit passability (once doors exist)
                passable_exits = {self.room_to_type_dict[instance]: [] for instance in present_exits}
                for instance in present_exits:
                    passable_exits[self.room_to_type_dict[instance]].append(instance)
                # print("passable exits:", passable_exits)
                if action_dict['arg1'] not in passable_exits:
                    # print(f"There is no exit to {action_dict['arg1']}!")
                    fail_dict: dict = {'phase': "resolution", 'fail_type': "no_exit_to", 'arg': action_dict['arg1']}
                    no_exit_to_str: str = f"There is no passage to a {self.room_types[action_dict['arg1']]['repr_str']} here."
                    return False, no_exit_to_str, fail_dict
                elif len(passable_exits[action_dict['arg1']]) > 1:
                    # print(f"There are multiple {action_dict['arg1']}!")
                    # TODO: handle multiple instances of same entity type -> going for adjective solution for now
                    fail_dict: dict = {'phase': "resolution", 'fail_type': "multiple_exits_to", 'arg': action_dict['arg1']}
                    return False, f"There are multiple {self.room_types[action_dict['arg1']]['repr_str']}s here.", fail_dict
                else:
                    arg1_inst = passable_exits[action_dict['arg1']][0]

                pre_state: str = state_change['pre_state'].replace("HERE", self.get_player_room())

                if "PLAYER" in pre_state:
                    pre_state = pre_state.replace("PLAYER", "player1")
                    pre_state_tuple = fact_str_to_tuple(pre_state)

                    post_state: str = state_change['post_state'].replace("TARGET", arg1_inst)
                    post_state = post_state.replace("PLAYER", "player1")
                    post_state_tuple = fact_str_to_tuple(post_state)
                    # facts_to_add.append(post_state_tuple)

                    # check conditions:
                    conditions_fulfilled: bool = True
                    for condition in state_change['conditions']:
                        player_condition = condition.replace("HERE", self.get_player_room())
                        player_condition = player_condition.replace("TARGET", arg1_inst)
                        # print("player condition:", player_condition)
                        player_condition_tuple = fact_str_to_tuple(player_condition)
                        if player_condition_tuple not in self.world_state:
                            conditions_fulfilled = False

                    # TODO: give conditions feedback

                    if conditions_fulfilled:
                        facts_to_remove.append(pre_state_tuple)
                        facts_to_add.append(post_state_tuple)

                    # facts_to_remove.append(pre_state_tuple)

                if "THING" in pre_state:
                    # pre_state = pre_state.replace("HERE", self.get_player_room())
                    # check things at location:
                    internal_visible_contents = self.get_player_room_contents_visible()
                    # print("vis cont type:", type(internal_visible_contents))
                    # print("inv cont type:", type(self.get_inventory_content()))
                    # things_here = set(self.get_player_room_contents_visible()) | self.get_inventory_content()
                    # print("things here:", things_here)
                    for thing_here in things_here:
                        pre_state: str = state_change['pre_state'].replace("HERE", self.get_player_room())
                        # print("initial prestate:", pre_state)
                        # print("current thing here:", thing_here)
                        pre_state = pre_state.replace("THING", thing_here)
                        # print("current prestate for thing here:", pre_state)
                        pre_state_tuple = fact_str_to_tuple(pre_state)
                        # print("current prestate tuple for thing here:", pre_state_tuple)

                        post_state: str = state_change['post_state'].replace("TARGET", arg1_inst)
                        post_state = post_state.replace("THING", thing_here)
                        post_state_tuple = fact_str_to_tuple(post_state)

                        # check conditions
                        conditions_fulfilled: bool = True
                        for condition in state_change['conditions']:
                            thing_condition = condition.replace("THING", thing_here)
                            thing_condition_tuple = fact_str_to_tuple(thing_condition)
                            if thing_condition_tuple not in self.world_state:
                                conditions_fulfilled = False

                        # TODO: give conditions feedback

                        if conditions_fulfilled:
                            facts_to_remove.append(pre_state_tuple)
                            facts_to_add.append(post_state_tuple)
                        # print()

                # print("facts to remove after HERE block:", facts_to_remove)
                # print("facts to add after HERE block:", facts_to_add)

                state_changed = True

            elif "THING" in state_change['pre_state'] or "THING" in state_change['post_state']:
                # ENTITY ACCESSIBILITY
                # get visible room content:
                internal_visible_contents = self.get_player_room_contents_visible()

                # get inventory content:
                inventory_content = self.get_inventory_content()
                # print(inventory_content)

                # convert to types:
                # print("internal visible contents:", internal_visible_contents)
                accessible_contents = {self.inst_to_type_dict[instance]: [] for instance in internal_visible_contents}
                for instance in internal_visible_contents:
                    accessible_contents[self.inst_to_type_dict[instance]].append(instance)
                for inventory_item in inventory_content:
                    if self.inst_to_type_dict[inventory_item] not in accessible_contents:
                        accessible_contents[self.inst_to_type_dict[inventory_item]] = []
                    accessible_contents[self.inst_to_type_dict[inventory_item]].append(inventory_item)
                # print("player room:", self.get_player_room())
                # add floor to 'visible' contents to allow taking from floor:
                accessible_contents["floor"] = [f"{self.get_player_room()}floor"]
                # print("visible contents:", accessible_contents)

                # print(action_dict)
                if action_dict['type'] == "take":
                    for inventory_item in inventory_content:
                        # print(inventory_item)
                        if self.inst_to_type_dict[inventory_item] == action_dict['arg1']:
                            # print("already in inventory")
                            fail_dict: dict = {'phase': "resolution", 'fail_type': "entity_already_inventory",
                                               'arg': action_dict['arg1']}
                            return False, f"The {self.entity_types[action_dict['arg1']]['repr_str']} is already in your inventory.", fail_dict
                    # if action_dict['arg2'] == "inventory":
                    #    print("taking from inventory")

                # arg1 = self.repr_str_to_type_dict[action_dict['arg1']]
                arg1 = action_dict['arg1']
                # if action_dict['arg1'] not in accessible_contents:
                if arg1 not in accessible_contents:
                    # print(f"There is no {action_dict['arg1']}!")
                    fail_dict: dict = {'phase': "resolution", 'fail_type': "entity_not_accessible",
                                       'arg': action_dict['arg1']}
                    # return False, f"There is no {self.entity_types[action_dict['arg1']]['repr_str']} here.", fail_dict

                    return False, f"There is no {self.entity_types[arg1]['repr_str']} here.", fail_dict
                # elif len(accessible_contents[action_dict['arg1']]) > 1:
                elif len(accessible_contents[arg1]) > 1:
                    # print(f"There are multiple {action_dict['arg1']}!")
                    fail_dict: dict = {'phase': "resolution", 'fail_type': "multiple_entity_ambiguity",
                                       'arg': action_dict['arg1']}
                    # TODO: handle multiple instances of same entity type
                    return False, f"There are multiple {self.entity_types[arg1]['repr_str']} here.", fail_dict
                else:
                    # arg1_inst = accessible_contents[action_dict['arg1']][0]
                    arg1_inst = accessible_contents[arg1][0]

                arg2_inst = None
                if 'arg2' in action_dict:
                    # arg2 = self.repr_str_to_type_dict[action_dict['arg2']]
                    arg2 = action_dict['arg2']
                    # if action_dict['arg2'] not in accessible_contents:
                    if arg2 not in accessible_contents:
                        # print(f"There is no {action_dict['arg2']}!")
                        fail_dict: dict = {'phase': "resolution", 'fail_type': "entity_not_accessible",
                                           'arg': action_dict['arg2']}
                        # thing_not_accessible_str: str = f"There is no {self.entity_types[action_dict['arg2']]['repr_str']} here."
                        thing_not_accessible_str: str = f"There is no {self.entity_types[arg2]['repr_str']} here."
                        return False, thing_not_accessible_str, fail_dict
                    # elif len(accessible_contents[action_dict['arg2']]) > 1:
                    elif len(accessible_contents[arg2]) > 1:
                        # print(f"There are multiple {action_dict['arg2']}!")
                        # TODO: handle multiple instances of same entity type
                        fail_dict: dict = {'phase': "resolution", 'fail_type': "multiple_entity_ambiguity",
                                           'arg': action_dict['arg2']}
                        return False, f"There are multiple {self.entity_types[arg2]['repr_str']} here.", fail_dict
                    else:
                        # arg2_inst = accessible_contents[action_dict['arg2']][0]
                        arg2_inst = accessible_contents[arg2][0]

                # replace string placeholders with fact IDs:
                pre_state: str = state_change['pre_state'].replace("THING", arg1_inst)

                if "ANY" in pre_state:
                    # print("ANY found in precondition")
                    any_match = False
                    pred = fact_str_to_tuple(pre_state)[0]
                    for state_pred in self.world_state:
                        if state_pred[0] == pred and state_pred[1] == arg1_inst:
                            # print(state_pred)
                            any_match = True
                            pre_state = pre_state.replace("ANY", state_pred[2])
                            # print(pre_state)
                            break
                    if not any_match:
                        # print("no matching pred for ANY found")
                        continue


                # print("pre state:", pre_state)
                post_state: str = state_change['post_state'].replace("THING", arg1_inst)

                if "PREP" in post_state:
                    post_state = post_state.replace("PREP", action_dict['prep'])

                if "TARGET" in post_state:
                    post_state = post_state.replace("TARGET", arg2_inst)

                # print("post state:", post_state)

                # check conditions

                # convert to fact tuples:
                pre_state_tuple = fact_str_to_tuple(pre_state)
                post_state_tuple = fact_str_to_tuple(post_state)

                # check conditions:
                conditions_fulfilled: bool = True
                for condition in state_change['conditions']:
                    thing_condition = condition.replace("THING", arg1_inst)
                    if arg2_inst:
                        thing_condition = thing_condition.replace("TARGET", arg2_inst)
                    # print("thing condition:", thing_condition)
                    thing_condition_tuple = fact_str_to_tuple(thing_condition)
                    # print("thing condition tuple:", thing_condition_tuple)
                    if thing_condition_tuple not in self.world_state:
                        # print(thing_condition_tuple, "not in world state")
                        conditions_fulfilled = False

                # TODO: give conditions feedback

                if conditions_fulfilled:
                    # print("conditions fulfilled:", state_change['conditions'])
                    facts_to_remove.append(pre_state_tuple)
                    facts_to_add.append(post_state_tuple)


                # facts_to_remove.append(pre_state_tuple)
                # facts_to_add.append(post_state_tuple)

                # remove pre state and add post state:
                # self.world_state.remove(pre_state_tuple)
                # self.world_state.add(post_state_tuple)

                state_changed = True

        # print("facts to remove:", facts_to_remove)
        # print("facts to add:", facts_to_add)

        for remove_fact in facts_to_remove:
            if remove_fact in self.world_state:
                self.world_state.remove(remove_fact)
            else:
                # TODO: handle commands removing facts that don't hold
                pass
        for add_fact in facts_to_add:
            self.world_state.add(add_fact)

        # add current world state to world state history:
        self.world_state_history.append(deepcopy(self.world_state))

        if state_changed:
            # TODO: make second return item more useful
            return True, facts_to_add[0], {}
        else:
            # TODO: make this proper pre_state/conditions feedback
            fail_dict: dict = {'phase': "resolution", 'fail_type': "pre_state_mismatch",
                               'arg': [action_dict['arg1'], pre_state]}
            return False, f"{action_dict['arg1']} is not {pre_state}", fail_dict

    def process_action(self, action_input: str):
        """
        Fully process an action input.
        """
        # print("Old world state:", self.world_state)

        # goals_achieved = set()

        parsed, parse_result, fail = self.parse_action_input(action_input)
        if not parsed:
            return self.goals_achieved, parse_result, fail
        else:
            prior_visibles = set(self.get_player_room_contents_visible())
            # print("Prior visibles:", prior_visibles)
            resolved, resolution_result, fail = self.resolve_action(parse_result)
            if not resolved:
                return self.goals_achieved, resolution_result, fail
            else:
                # print("resolution result:", resolution_result)
                # get template:
                feedback_template = self.action_types[parse_result['type']]['feedback_template']
                # print("feedback template:", feedback_template)
                feedback_jinja = jinja2.Template(feedback_template)
                template_tags = ["thing", "inventory_desc", "prep", "target", "room_desc"]
                # TODO?: externalize template tags?
                jinja_args = dict()
                for template_tag in template_tags:
                    if template_tag in feedback_template:
                        if template_tag == "thing":
                            jinja_args[template_tag] = self._get_inst_str(resolution_result[1])
                        if template_tag == "inventory_desc":
                            jinja_args[template_tag] = self.get_inventory_desc()
                        if template_tag == "prep":
                            jinja_args[template_tag] = resolution_result[0]
                        if template_tag == "target":
                            # print("template tag target found!")
                            # print("res result item 2:", resolution_result[2])
                            jinja_args[template_tag] = self._get_inst_str(resolution_result[2])
                        if template_tag == "room_desc":
                            # print("template tag room_desc found!")
                            jinja_args[template_tag] = self.get_full_room_desc()
                base_result_str = feedback_jinja.render(jinja_args)

                # print("base result string after jinja:", base_result_str)

                # check goal achievement:
                # print("goals:", self.goal_state)
                self.goals_achieved = self.goal_state & self.world_state
                goals_achieved_response = list(self.goal_state & self.world_state)
                # print("goals achieved:", self.goals_achieved)
                # convert to goal states to string version:
                for goal_state_idx, goal_state in enumerate(goals_achieved_response):
                    # print("loop goal state:", goal_state)
                    goals_achieved_response[goal_state_idx] = fact_tuple_to_str(goal_state)
                    # print("loop goal state post:", goal_state)
                goals_achieved_response = set(goals_achieved_response)

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
                        for fact in self.world_state:
                            if fact[0] == 'in' and fact[1] == thing:
                                # visible_content_state_strs.append(f"There is a {thing} in the {fact[2]}.")
                                # visible_content_state_strs.append(f"There is a {self.inst_to_type_dict[thing]} in the {self.inst_to_type_dict[fact[2]]}.")
                                visible_content_state_strs.append(f"There is a {self._get_inst_str(thing)} in the {self._get_inst_str(fact[2])}.")
                    visible_content_state_combined = " ".join(visible_content_state_strs)
                    if visible_content_state_combined:
                        # print("visible_content_state_combined is a thing!")
                        visible_content_state_combined = " " + visible_content_state_combined
                    # print("New world state:", self.world_state)
                    # return goals_achieved_response, f"{base_result_str} {visible_content_state_combined}", {}
                    return goals_achieved_response, f"{base_result_str}{visible_content_state_combined}", {}
                else:
                    # print("New world state:", self.world_state)
                    return goals_achieved_response, base_result_str, {}

    def execute_optimal_solution(self):
        """
        Run through the game_instance's optimal solution.
        Used to verify parity of IF interpreter and solution generation.
        """
        print(self.get_full_room_desc())
        for command in self.game_instance["optimal_commands"]:
            print(f"> {command}")
            goals_achieved, response, fail = self.process_action(command)
            print(response)
            print("Goals achieved:", goals_achieved)
            print("Fail:", fail)
            print()

    def execute_plan_sequence(self, command_sequence: list):
        """
        Execute a command sequence plan and return results up to first failure.
        """
        result_sequence: list = list()
        world_state_change_count: int = 0
        for cmd_idx, command in enumerate(command_sequence):
            result = self.process_action(command)
            # result[2] is fail info; if it is truthy, the command failed
            result_sequence.append(result)
            # check for command failure:
            if result[2]:
                # stop executing commands at the first failure
                break
            else:
                world_state_change_count += 1

        # revert the world state to before plan execution if it changed:
        if world_state_change_count:
            self.world_state_history = self.world_state_history[:-world_state_change_count]
            # pre_plan_world_state = self.world_state_history[-world_state_change_count]
            self.world_state = self.world_state_history[-1]

        return result_sequence


if __name__ == "__main__":
    PATH = ""
    """
    game_instance_exmpl = {"game_id": 11, "variant": "basic",
     "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the single action you want to take in the game starting with >. Only reply with actions.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put the book on the table, the plate on the table and the mop on the table.\n\n",
     "initial_state": ["at(kitchen1floor,kitchen1)", "at(pantry1floor,pantry1)", "at(hallway1floor,hallway1)",
                       "at(livingroom1floor,livingroom1)", "at(broomcloset1floor,broomcloset1)",
                       "at(bedroom1floor,bedroom1)", "at(table1,livingroom1)", "at(sidetable1,livingroom1)",
                       "at(counter1,kitchen1)", "at(refrigerator1,pantry1)", "at(cupboard1,kitchen1)",
                       "at(wardrobe1,bedroom1)", "at(shelf1,livingroom1)", "at(freezer1,pantry1)",
                       "at(pottedplant1,hallway1)", "at(chair1,livingroom1)", "at(bed1,bedroom1)",
                       "at(couch1,livingroom1)", "at(broom1,broomcloset1)", "at(mop1,broomcloset1)",
                       "at(sandwich1,pantry1)", "at(apple1,pantry1)", "at(banana1,pantry1)", "at(orange1,pantry1)",
                       "at(peach1,pantry1)", "at(plate1,kitchen1)", "at(book1,livingroom1)", "at(pillow1,bedroom1)",
                       "at(player1,bedroom1)", "type(kitchen1floor,floor)", "type(pantry1floor,floor)",
                       "type(hallway1floor,floor)", "type(livingroom1floor,floor)", "type(broomcloset1floor,floor)",
                       "type(bedroom1floor,floor)", "type(player1,player)", "type(table1,table)",
                       "type(sidetable1,sidetable)", "type(counter1,counter)", "type(refrigerator1,refrigerator)",
                       "type(cupboard1,cupboard)", "type(wardrobe1,wardrobe)", "type(shelf1,shelf)",
                       "type(freezer1,freezer)", "type(pottedplant1,pottedplant)", "type(chair1,chair)",
                       "type(bed1,bed)", "type(couch1,couch)", "type(broom1,broom)", "type(mop1,mop)",
                       "type(sandwich1,sandwich)", "type(apple1,apple)", "type(banana1,banana)", "type(orange1,orange)",
                       "type(peach1,peach)", "type(plate1,plate)", "type(book1,book)", "type(pillow1,pillow)",
                       "room(kitchen1,kitchen)", "room(pantry1,pantry)", "room(hallway1,hallway)",
                       "room(livingroom1,livingroom)", "room(broomcloset1,broomcloset)", "room(bedroom1,bedroom)",
                       "support(kitchen1floor)", "support(pantry1floor)", "support(hallway1floor)",
                       "support(livingroom1floor)", "support(broomcloset1floor)", "support(bedroom1floor)",
                       "support(table1)", "support(sidetable1)", "support(counter1)", "support(shelf1)",
                       "support(bed1)", "on(book1,sidetable1)", "on(plate1,kitchen1floor)",
                       "on(mop1,broomcloset1floor)", "on(broom1,broomcloset1floor)", "on(pottedplant1,hallway1floor)",
                       "container(refrigerator1)", "container(cupboard1)", "container(wardrobe1)",
                       "container(freezer1)", "in(pillow1,wardrobe1)", "in(peach1,refrigerator1)",
                       "in(orange1,refrigerator1)", "in(banana1,refrigerator1)", "in(apple1,refrigerator1)",
                       "in(sandwich1,refrigerator1)", "exit(kitchen1,pantry1)", "exit(kitchen1,livingroom1)",
                       "exit(kitchen1,hallway1)", "exit(pantry1,kitchen1)", "exit(hallway1,kitchen1)",
                       "exit(hallway1,livingroom1)", "exit(hallway1,broomcloset1)", "exit(livingroom1,kitchen1)",
                       "exit(livingroom1,hallway1)", "exit(broomcloset1,hallway1)", "exit(bedroom1,livingroom1)",
                       "exit(livingroom1,bedroom1)", "openable(refrigerator1)", "openable(cupboard1)",
                       "openable(wardrobe1)", "openable(freezer1)", "closed(refrigerator1)", "closed(cupboard1)",
                       "closed(wardrobe1)", "closed(freezer1)", "takeable(pottedplant1)", "takeable(broom1)",
                       "takeable(mop1)", "takeable(sandwich1)", "takeable(apple1)", "takeable(banana1)",
                       "takeable(orange1)", "takeable(peach1)", "takeable(plate1)", "takeable(book1)",
                       "takeable(pillow1)", "movable(pottedplant1)", "movable(broom1)", "movable(mop1)",
                       "movable(sandwich1)", "movable(apple1)", "movable(banana1)", "movable(orange1)",
                       "movable(peach1)", "movable(plate1)", "movable(book1)", "movable(pillow1)",
                       "needs_support(pottedplant1)", "needs_support(broom1)", "needs_support(mop1)",
                       "needs_support(sandwich1)", "needs_support(apple1)", "needs_support(banana1)",
                       "needs_support(orange1)", "needs_support(peach1)", "needs_support(plate1)",
                       "needs_support(book1)", "needs_support(pillow1)"],
     "goal_state": ["on(book1,table1)", "on(plate1,table1)", "on(mop1,table1)"], "max_turns": 50, "optimal_turns": 12,
     "optimal_solution": [["go", "livingroom1"], ["put", "book1", "table1"], ["go", "kitchen1"], ["take", "plate1"],
                          ["go", "livingroom1"], ["put", "plate1", "table1"], ["go", "hallway1"],
                          ["go", "broomcloset1"], ["take", "mop1"], ["go", "hallway1"], ["go", "livingroom1"],
                          ["put", "mop1", "table1"]],
     "optimal_commands": ["go living room", "put book on table", "go kitchen", "take plate", "go living room",
                          "put plate on table", "go hallway", "go broom closet", "take mop", "go hallway",
                          "go living room", "put mop on table"], "action_definitions": ["basic_actions.json"],
     "room_definitions": ["home_rooms.json"], "entity_definitions": ["home_entities.json"]}
    """
    game_instance_exmpl = {"game_id": 11, "variant": "basic",
                           "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the single action you want to take in the game starting with >. Only reply with actions.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put the book on the table, the plate on the table and the mop on the table.\n\n",
                           "initial_state": ["at(kitchen1floor,kitchen1)", "at(pantry1floor,pantry1)",
                                             "at(hallway1floor,hallway1)",
                                             "at(livingroom1floor,livingroom1)", "at(broomcloset1floor,broomcloset1)",
                                             "at(bedroom1floor,bedroom1)", "at(table1,livingroom1)",
                                             "at(sidetable1,livingroom1)",
                                             "at(counter1,kitchen1)", "at(refrigerator1,pantry1)",
                                             "at(cupboard1,kitchen1)",
                                             "at(wardrobe1,bedroom1)", "at(shelf1,livingroom1)", "at(freezer1,pantry1)",
                                             "at(pottedplant1,hallway1)", "at(chair1,livingroom1)", "at(bed1,bedroom1)",
                                             "at(couch1,livingroom1)", "at(broom1,broomcloset1)",
                                             "at(mop1,broomcloset1)",
                                             "at(sandwich1,pantry1)", "at(apple1,pantry1)", "at(banana1,pantry1)",
                                             "at(orange1,pantry1)",
                                             "at(peach1,pantry1)", "at(plate1,kitchen1)", "at(book1,livingroom1)",
                                             "at(pillow1,bedroom1)",
                                             "at(player1,hallway1)", "type(kitchen1floor,floor)",
                                             "type(pantry1floor,floor)",
                                             "type(hallway1floor,floor)", "type(livingroom1floor,floor)",
                                             "type(broomcloset1floor,floor)",
                                             "type(bedroom1floor,floor)", "type(player1,player)", "type(table1,table)",
                                             "type(sidetable1,sidetable)", "type(counter1,counter)",
                                             "type(refrigerator1,refrigerator)",
                                             "type(cupboard1,cupboard)", "type(wardrobe1,wardrobe)",
                                             "type(shelf1,shelf)",
                                             "type(freezer1,freezer)", "type(pottedplant1,pottedplant)",
                                             "type(chair1,chair)",
                                             "type(bed1,bed)", "type(couch1,couch)", "type(broom1,broom)",
                                             "type(mop1,mop)",
                                             "type(sandwich1,sandwich)", "type(apple1,apple)", "type(banana1,banana)",
                                             "type(orange1,orange)",
                                             "type(peach1,peach)", "type(plate1,plate)", "type(book1,book)",
                                             "type(pillow1,pillow)",
                                             "room(kitchen1,kitchen)", "room(pantry1,pantry)", "room(hallway1,hallway)",
                                             "room(livingroom1,livingroom)", "room(broomcloset1,broomcloset)",
                                             "room(bedroom1,bedroom)",
                                             "support(kitchen1floor)", "support(pantry1floor)",
                                             "support(hallway1floor)",
                                             "support(livingroom1floor)", "support(broomcloset1floor)",
                                             "support(bedroom1floor)",
                                             "support(table1)", "support(sidetable1)", "support(counter1)",
                                             "support(shelf1)",
                                             "support(bed1)", "on(book1,sidetable1)", "on(plate1,kitchen1floor)",
                                             "on(mop1,broomcloset1floor)", "on(broom1,broomcloset1floor)",
                                             "on(pottedplant1,hallway1floor)",
                                             "container(refrigerator1)", "container(cupboard1)", "container(wardrobe1)",
                                             "container(freezer1)", "in(pillow1,wardrobe1)", "in(peach1,refrigerator1)",
                                             "in(orange1,refrigerator1)", "in(banana1,refrigerator1)",
                                             "in(apple1,refrigerator1)",
                                             "in(sandwich1,refrigerator1)", "exit(kitchen1,pantry1)",
                                             "exit(kitchen1,livingroom1)",
                                             "exit(kitchen1,hallway1)", "exit(pantry1,kitchen1)",
                                             "exit(hallway1,kitchen1)",
                                             "exit(hallway1,livingroom1)", "exit(hallway1,broomcloset1)",
                                             "exit(livingroom1,kitchen1)",
                                             "exit(livingroom1,hallway1)", "exit(broomcloset1,hallway1)",
                                             "exit(bedroom1,livingroom1)",
                                             "exit(livingroom1,bedroom1)", "openable(refrigerator1)",
                                             "openable(cupboard1)",
                                             "openable(wardrobe1)", "openable(freezer1)", "closed(refrigerator1)",
                                             "closed(cupboard1)",
                                             "closed(wardrobe1)", "closed(freezer1)", "takeable(pottedplant1)",
                                             "takeable(broom1)",
                                             "takeable(mop1)", "takeable(sandwich1)", "takeable(apple1)",
                                             "takeable(banana1)",
                                             "takeable(orange1)", "takeable(peach1)", "takeable(plate1)",
                                             "takeable(book1)",
                                             "takeable(pillow1)", "movable(pottedplant1)", "movable(broom1)",
                                             "movable(mop1)",
                                             "movable(sandwich1)", "movable(apple1)", "movable(banana1)",
                                             "movable(orange1)",
                                             "movable(peach1)", "movable(plate1)", "movable(book1)", "movable(pillow1)",
                                             "needs_support(pottedplant1)", "needs_support(broom1)",
                                             "needs_support(mop1)",
                                             "needs_support(sandwich1)", "needs_support(apple1)",
                                             "needs_support(banana1)",
                                             "needs_support(orange1)", "needs_support(peach1)", "needs_support(plate1)",
                                             "needs_support(book1)", "needs_support(pillow1)"],
                           "goal_state": ["on(book1,table1)", "on(plate1,table1)", "on(mop1,table1)"], "max_turns": 50,
                           "optimal_turns": 12,
                           "optimal_solution": [["go", "livingroom1"], ["put", "book1", "table1"], ["go", "kitchen1"],
                                                ["take", "plate1"],
                                                ["go", "livingroom1"], ["put", "plate1", "table1"], ["go", "hallway1"],
                                                ["go", "broomcloset1"], ["take", "mop1"], ["go", "hallway1"],
                                                ["go", "livingroom1"],
                                                ["put", "mop1", "table1"]],
                           "optimal_commands": ["go living room", "put book on table", "go kitchen", "take plate",
                                                "go living room",
                                                "put plate on table", "go hallway", "go broom closet", "take mop",
                                                "go hallway",
                                                "go living room", "put mop on table"],
                           "action_definitions": ["basic_actions.json"],
                           "room_definitions": ["home_rooms.json"], "entity_definitions": ["home_entities.json"]}

    test_interpreter = AdventureIFInterpreter(game_instance_exmpl)
    # test_interpreter = AdventureIFInterpreter(game_instance_exmpl, verbose=True)

    # test_interpreter.execute_optimal_solution()

    # print(test_interpreter.action_types)
    # print(test_interpreter.entity_types)

    print(test_interpreter.get_full_room_desc())

    turn_1 = test_interpreter.process_action("take potted plant")
    print(turn_1)
    print()

    """
    turn_1_world_state = deepcopy(test_interpreter.world_state)

    # turn_1_plan = ["take pillow"]
    # turn_1_plan = ["take pillow", "go living room"]
    # turn_1_plan = ["take pillow", "go kitchen"]
    turn_1_plan = ["take pillow", "go kitchen", "take plate"]

    plan_response = test_interpreter.execute_plan_sequence(turn_1_plan)
    print(plan_response)

    world_properly_reverted = test_interpreter.world_state == turn_1_world_state
    print(f"world state properly reverted:", world_properly_reverted)
    """
    """
    turn_2 = test_interpreter.process_action("take pillow")
    print(turn_2)
    print()

    turn_3 = test_interpreter.process_action("go living room")
    print(turn_3)
    print()

    turn_4 = test_interpreter.process_action("take book from side table")
    print(turn_4)
    print()

    turn_5 = test_interpreter.process_action("put book on table")
    print(turn_5)
    print()

    turn_6 = test_interpreter.process_action("put plate on table")
    print(turn_6)
    print()

    turn_7 = test_interpreter.process_action("take plate from kitchen")
    print(turn_7)
    """

