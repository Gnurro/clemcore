"""
    Module wrapping IF interpreter(s) for adventuregame.
"""

# TODO: entity states (colors, materials, etc)

import json
import lark
from lark import Lark, Transformer
import jinja2


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


def state_tuple_to_str(state_tuple: tuple, value_delimiter_l: str = "(", value_separator: str = ",",
                       value_delimiter_r: str = ")",):
    """
    Convert state predicate tuple to string version.
    """
    values = state_tuple[1:]
    # print(values)
    values_str = value_separator.join(values)
    # print(values_str)
    state_str = f"{state_tuple[0]}{value_delimiter_l}{values_str}{value_delimiter_r}"
    return state_str


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
                if len(child.children) == 1:
                    arguments.append(child.children[0].value)
                else:
                    arguments.append(child.children[-1].value)
                    argument_adjs = [adj.value for adj in child.children[:-1] if adj.type == 'ADJ']
                    # print(argument_adjs)
                    if argument_adjs:
                        action_dict[f'arg{arg_idx}_adjs'] = argument_adjs

                action_dict[f'arg{arg_idx}'] = arguments[-1]

                arg_idx += 1
            if type(child) == lark.Token and child.type == 'PREP':
                action_dict['prep'] = child.value

        return action_dict


class BasicIFInterpreter:
    """
    A basic IF interpreter for adventuregame.
    """
    def __init__(self, game_instance: dict):
        self.game_instance: dict = game_instance

        self.entity_types = dict()
        self.initialize_entity_types()
        # print(self.entity_types)

        self.room_types = dict()
        self.initialize_room_types()

        self.action_types = dict()
        self.initialize_action_types()
        # print(self.action_types)

        self.world_state: set = set()
        self.goal_state: set = set()
        self.goals_achieved: set = set()
        self.initialize_states_from_strings()

        self.initialize_action_parsing()

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
        # TODO: use clemgame resource loading
        # load basic entity types:
        with open(f"{PATH}resources/basic_entities.json", 'r', encoding='utf-8') as entities_file:
            entity_definitions = json.load(entities_file)
            for entity_definition in entity_definitions:
                self.entity_types[entity_definition['type_name']] = dict()
                for entity_attribute in entity_definition:
                    if not entity_attribute == 'type_name':
                        self.entity_types[entity_definition['type_name']][entity_attribute] = entity_definition[
                            entity_attribute]

    def initialize_room_types(self):
        """
        Load and process room types in this adventure.
        """
        # TODO: use clemgame resource loading
        # load basic entity types:
        with open(f"{PATH}resources/basic_rooms.json", 'r', encoding='utf-8') as rooms_file:
            room_definitions = json.load(rooms_file)
            for room_definition in room_definitions:
                self.room_types[room_definition['type_name']] = dict()
                for room_attribute in room_definition:
                    if not room_attribute == 'type_name':
                        self.room_types[room_definition['type_name']][room_attribute] = room_definition[
                            room_attribute]

    def initialize_action_types(self):
        """
        Load and process action types in this adventure.
        """
        # TODO: use clemgame resource loading
        # load basic action types:
        # with open(f"{PATH}resources/basic_actions1.json", 'r', encoding='utf-8') as actions_file:
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

    def initialize_action_parsing(self):
        """
        Initialize the lark action input parser and transformer.
        """

        # TODO: excise grammar init -> get adjectives from world state or entity defs

        # TODO: define applicable instance adj states in entity type def? -> predefines set of adjs

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

        act_grammar_adj_line = f"ADJ: {' | '.join(all_adjs)}\n"

        # print(act_grammar_adj_line)

        # TODO: use clemgame resource loading

        with open(f"{PATH}resources/grammar_core.json", 'r', encoding='utf-8') as grammar_core_file:
            grammar_core = json.load(grammar_core_file)
            grammar_head = grammar_core['grammar_head']
            grammar_foot = grammar_core['grammar_foot']

        act_grammar = (f"{grammar_head}{act_grammar_action_line}"
                       f"{act_grammar_larks_str}\n{act_grammar_adj_line}{grammar_foot}")

        # print(act_grammar)

        self.act_parser = Lark(act_grammar, start='action')
        self.act_transformer = IFTransformer()

    def initialize_states_from_strings(self):
        """
        Convert List[Str] world state format into Set[Tuple].
        """
        for state_string in self.game_instance['initial_state']:
            self.world_state.add(split_state_string(state_string))

        # print("unaugmented initial world:", self.world_state)

        preds_to_add = set()

        # add trait facts for objects:
        for state_pred in self.world_state:
            if state_pred[0] == 'type':
                # add trait facts by entity type:
                if 'traits' in self.entity_types[state_pred[2]]:
                    type_traits: list = self.entity_types[state_pred[2]]['traits']
                    for type_trait in type_traits:
                        preds_to_add.add((type_trait, state_pred[1]))
                """"""

        # add floors to rooms:
        for state_pred in self.world_state:
            if state_pred[0] == 'room':
                # print("room to add floor to found:", state_pred)
                preds_to_add.add(('type', f'{state_pred[1]}floor', 'floor'))
                preds_to_add.add(('at', f'{state_pred[1]}floor', state_pred[1]))
                # print("pred to add:", preds_to_add)

        self.world_state = self.world_state.union(preds_to_add)

        # get entity instance types from world state:
        self.inst_to_type_dict = dict()
        for state_pred in self.world_state:
            # entity instance to entity type mapping:
            if state_pred[0] == 'type':
                # print("type set:", state_pred)
                self.inst_to_type_dict[state_pred[1]] = state_pred[2]

        # get room instance types from world state:
        self.room_to_type_dict = dict()
        for state_pred in self.world_state:
            # room instance to room type mapping:
            if state_pred[0] == 'room':
                # print("type set:", state_pred)
                self.room_to_type_dict[state_pred[1]] = state_pred[2]

        # put 'supported' items on the floor if they are not 'in' or 'on':
        for state_pred in self.world_state:
            # print("checking", state_pred)
            if state_pred[1] in self.inst_to_type_dict:
                if self.inst_to_type_dict[state_pred[1]] in self.entity_types:
                    # print(self.entity_types[self.inst_to_type_dict[state_pred[1]]])
                    pass
            # if state_pred[0] == 'at' and hasattr(self.entity_types[self.inst_to_type_dict[state_pred[1]]], 'supported'):
            # if state_pred[0] == 'at' and 'supported' in self.entity_types[self.inst_to_type_dict[state_pred[1]]]:
            if state_pred[0] == 'at' and ('needs_support', state_pred[1]) in self.world_state:
                # print("needs support:", state_pred)
                currently_supported = False
                for state_pred2 in self.world_state:
                    if state_pred2[0] == 'on' and state_pred2[1] == state_pred[1]:
                        currently_supported = True
                        break
                    if state_pred2[0] == 'in' and state_pred2[1] == state_pred[1]:
                        currently_supported = True
                        break
                if not currently_supported:
                    # self.world_state.add(('on', 'floor', state_pred[2]))
                    # preds_to_add.add(('on', state_pred[1], 'floor'))
                    preds_to_add.add(('on', state_pred[1], f'{state_pred[2]}floor'))

        self.world_state = self.world_state.union(preds_to_add)

        # print("augmented initial world:", self.world_state)

        for state_string in self.game_instance['goal_state']:
            self.goal_state.add(split_state_string(state_string))

    def _get_inst_str(self, inst):
        """
        Get a full string representation of an entity instance with adjectives.
        """
        inst_adjs = list()
        # get adj preds:
        for state_pred in self.world_state:
            if state_pred[0] == 'adj' and state_pred[1] == inst:
                inst_adjs.append(state_pred[2])

        inst_adjs.append(self.inst_to_type_dict[inst])

        adj_str = " ".join(inst_adjs)

        # full_inst_str = f"{adj_str} {self.inst_to_type_dict[inst]}"
        # full_inst_str = f"{adj_str} {self.inst_to_type_dict[inst]}"

        # return full_inst_str
        return adj_str

    def get_player_room(self):
        """
        Get the current room str.
        """
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[1] == 'player1':
                player_room = state_pred[2]
                break
        return player_room

    def get_player_room_contents(self):
        """
        Get all contents of the current room.
        """
        player_room = self.get_player_room()
        # print("player in room:", player_room)
        room_contents = list()
        for state_pred in self.world_state:
            if state_pred[0] == 'at' and state_pred[2] == player_room and not state_pred[1] == 'player1':
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

            if 'hidden' in self.entity_types[self.inst_to_type_dict[thing]]:
                continue

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
                            # TODO: figure out inventory item reporting; handling in action resolve now
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
        for state_pred in self.world_state:
            if state_pred[0] == 'exit' and state_pred[1] == player_room:
                room_exits.append(state_pred[2])
        return room_exits

    def get_full_room_desc(self):
        """
        Full description of the room the player is at.
        Handles entity visibility inside closed/open containers.
        """
        # get player room:
        player_room = self.get_player_room()
        # create room description start:
        player_at_str = f"You are in a {self.room_to_type_dict[player_room]}."

        # get visible room content:
        internal_visible_contents = self.get_player_room_contents_visible()

        # convert to types:
        # print("visible contents:", internal_visible_contents)
        # visible_contents = [self.inst_to_type_dict[instance] for instance in internal_visible_contents]
        visible_contents = [self._get_inst_str(instance) for instance in internal_visible_contents]

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
        if visible_content_state_strs:
            visible_content_state_combined = " ".join(visible_content_state_strs)
            visible_content_state_combined = " " + visible_content_state_combined
        else:
            visible_content_state_combined = str()

        # TODO: handle doors (once they exist)

        room_exits = self.get_player_room_exits()
        # convert target room IDs to type names:
        for target_room_idx, target_room in enumerate(room_exits):
            room_exits[target_room_idx] = self.room_to_type_dict[target_room]
        exits_str = str()
        if len(room_exits) == 1:
            # exits_str = f" You can go to a {room_exits[0]} from here."
            exits_str = f" There is a passage to a {room_exits[0]} here."
        elif len(room_exits) == 2:
            # exits_str = f" You can go to a {room_exits[0]} and a {room_exits[1]} from here."
            exits_str = f" There are passages to a {room_exits[0]} and a {room_exits[1]} here."
        elif len(room_exits) >= 3:
            comma_exits = ", a ".join(room_exits[:-1])
            # exits_str = f" You can go to {comma_exits} and {room_exits[-1]} from here."
            exits_str = f" There are passages to a {comma_exits} and a {room_exits[-1]} here."

        # combine full room description:
        # room_description = f"{player_at_str} {visible_contents_str} {visible_content_state_combined} {exits_str}"
        room_description = f"{player_at_str}{visible_contents_str}{visible_content_state_combined}{exits_str}"
        # room_description = " ".join([player_at_str, visible_contents_str, visible_content_state_combined, exits_str])

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
            inv_str = f"a {self.inst_to_type_dict[inv_list[0]]}"
        else:
            inv_strs = [f"a {self.inst_to_type_dict[inv_item]}" for inv_item in inv_list]
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
        """
        # simple split for now:
        action_tuple = tuple(action_input.split())
        # assume VO:
        if action_tuple[0] not in self.action_types:
            return False, f"I don't know what '{action_tuple[0]}' means."
        if action_tuple[1] not in self.entity_types:
            return False, f"I don't know what a '{action_tuple[1]}' is."
        """

        parsed_command = self.act_parser.parse(action_input)
        action_dict = self.act_transformer.transform(parsed_command)
        # print("parse action input arg:", action_dict)

        if action_dict['type'] not in self.action_types:
            return False, f"I don't know what '{action_dict['arg1']}' means."

        if action_dict['arg1'] not in self.entity_types:
            if action_dict['arg1'] not in self.room_types:
                return False, f"I don't know what a '{action_dict['arg1']}' is."

        if 'arg2' in action_dict:
            if action_dict['arg2'] not in self.entity_types:
                return False, f"I don't know what a '{action_dict['arg2']}' is."

        return True, action_dict

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

            if "HERE" in state_change['pre_state'] or "HERE" in state_change['post_state']:

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
                    return False, f"There is no exit to {action_dict['arg1']} here."
                elif len(passable_exits[action_dict['arg1']]) > 1:
                    # print(f"There are multiple {action_dict['arg1']}!")
                    # TODO: handle multiple instances of same entity type
                    return False, f"There are multiple {action_dict['arg1']} here."
                else:
                    arg1_inst = passable_exits[action_dict['arg1']][0]

                pre_state: str = state_change['pre_state'].replace("HERE", self.get_player_room())

                if "PLAYER" in pre_state:
                    pre_state = pre_state.replace("PLAYER", "player1")
                    pre_state_tuple = split_state_string(pre_state)

                    post_state: str = state_change['post_state'].replace("TARGET", arg1_inst)
                    post_state = post_state.replace("PLAYER", "player1")
                    post_state_tuple = split_state_string(post_state)
                    # facts_to_add.append(post_state_tuple)

                    # check conditions:
                    conditions_fulfilled: bool = True
                    for condition in state_change['conditions']:
                        player_condition = condition.replace("HERE", self.get_player_room())
                        player_condition = player_condition.replace("TARGET", arg1_inst)
                        # print("player condition:", player_condition)
                        player_condition_tuple = split_state_string(player_condition)
                        if player_condition_tuple not in self.world_state:
                            conditions_fulfilled = False

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
                        pre_state_tuple = split_state_string(pre_state)
                        # print("current prestate tuple for thing here:", pre_state_tuple)

                        post_state: str = state_change['post_state'].replace("TARGET", arg1_inst)
                        post_state = post_state.replace("THING", thing_here)
                        post_state_tuple = split_state_string(post_state)

                        # check conditions
                        conditions_fulfilled: bool = True
                        for condition in state_change['conditions']:
                            thing_condition = condition.replace("THING", thing_here)
                            thing_condition_tuple = split_state_string(thing_condition)
                            if thing_condition_tuple not in self.world_state:
                                conditions_fulfilled = False

                        if conditions_fulfilled:
                            facts_to_remove.append(pre_state_tuple)
                            facts_to_add.append(post_state_tuple)
                        # print()


                # print("pre state:", pre_state)
                """
                post_state: str = state_change['post_state'].replace("TARGET", arg1_inst)

                if "PLAYER" in post_state:
                    post_state = post_state.replace("PLAYER", "player1")
                    post_state_tuple = split_state_string(post_state)
                    facts_to_add.append(post_state_tuple)
                """
                # print("post state:", post_state)

                # print("facts to remove after HERE block:", facts_to_remove)
                # print("facts to add after HERE block:", facts_to_add)

                state_changed = True

            elif "THING" in state_change['pre_state'] or "THING" in state_change['post_state']:
                # get visible room content:
                internal_visible_contents = self.get_player_room_contents_visible()

                # get inventory content:
                inventory_content = self.get_inventory_content()
                # print(inventory_content)

                # convert to types:
                # print("internal visible contents:", internal_visible_contents)
                visible_contents = {self.inst_to_type_dict[instance]: [] for instance in internal_visible_contents}
                for instance in internal_visible_contents:
                    visible_contents[self.inst_to_type_dict[instance]].append(instance)
                for inventory_item in inventory_content:
                    if self.inst_to_type_dict[inventory_item] not in visible_contents:
                        visible_contents[self.inst_to_type_dict[inventory_item]] = []
                    visible_contents[self.inst_to_type_dict[inventory_item]].append(inventory_item)
                # print("visible contents:", visible_contents)

                # TODO: move multiples handling to parsing step

                if action_dict['arg1'] not in visible_contents:
                    print(f"There is no {action_dict['arg1']}!")
                    return False, f"There is no {action_dict['arg1']} here."
                elif len(visible_contents[action_dict['arg1']]) > 1:
                    print(f"There are multiple {action_dict['arg1']}!")
                    # TODO: handle multiple instances of same entity type
                    return False, f"There are multiple {action_dict['arg1']} here."
                else:
                    arg1_inst = visible_contents[action_dict['arg1']][0]

                arg2_inst = None
                if 'arg2' in action_dict:
                    if action_dict['arg2'] not in visible_contents:
                        print(f"There is no {action_dict['arg2']}!")
                        return False, f"There is no {action_dict['arg2']} here."
                    elif len(visible_contents[action_dict['arg2']]) > 1:
                        print(f"There are multiple {action_dict['arg2']}!")
                        # TODO: handle multiple instances of same entity type
                        return False, f"There are multiple {action_dict['arg2']} here."
                    else:
                        arg2_inst = visible_contents[action_dict['arg2']][0]

                # replace string placeholders with fact IDs:
                pre_state: str = state_change['pre_state'].replace("THING", arg1_inst)

                if "ANY" in pre_state:
                    # print("ANY found in precondition")
                    any_match = False
                    pred = split_state_string(pre_state)[0]
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
                pre_state_tuple = split_state_string(pre_state)
                post_state_tuple = split_state_string(post_state)

                # check conditions:
                conditions_fulfilled: bool = True
                for condition in state_change['conditions']:
                    thing_condition = condition.replace("THING", arg1_inst)
                    if arg2_inst:
                        thing_condition = thing_condition.replace("TARGET", arg2_inst)
                    # print("thing condition:", thing_condition)
                    thing_condition_tuple = split_state_string(thing_condition)
                    # print("thing condition tuple:", thing_condition_tuple)
                    if thing_condition_tuple not in self.world_state:
                        # print(thing_condition_tuple, "not in world state")
                        conditions_fulfilled = False

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
            self.world_state.remove(remove_fact)
        for add_fact in facts_to_add:
            self.world_state.add(add_fact)

        if state_changed:
            return True, facts_to_add[0]
        else:
            return False, f"{action_dict['arg1']} is not {pre_state}"

    def process_action(self, action_input: str):
        """
        Fully process an action input.
        """
        # print("Old world state:", self.world_state)

        # goals_achieved = set()

        parsed, parse_result = self.parse_action_input(action_input)
        if not parsed:
            return self.goals_achieved, parse_result
        else:
            prior_visibles = set(self.get_player_room_contents_visible())
            # print("Prior visibles:", prior_visibles)
            resolved, resolution_result = self.resolve_action(parse_result)
            if not resolved:
                return self.goals_achieved, resolution_result
            else:
                # print("resolution result:", resolution_result)
                # get template:
                feedback_template = self.action_types[parse_result['type']]['feedback_template']
                # print("feedback template:", feedback_template)
                feedback_jinja = jinja2.Template(feedback_template)
                template_tags = ["thing", "inventory_desc", "prep", "target", "room_desc"]
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
                            jinja_args[template_tag] = self._get_inst_str(resolution_result[2])
                        if template_tag == "room_desc":
                            jinja_args[template_tag] = self.get_full_room_desc()
                base_result_str = feedback_jinja.render(jinja_args)

                """
                if len(resolution_result) == 2:
                    # base_result_str = f"The {resolution_result[1]} is now {resolution_result[0]}."
                    base_result_str = f"The {self._get_inst_str(resolution_result[1])} is now {resolution_result[0]}."
                elif len(resolution_result) == 3 and resolution_result[2] == 'inventory':
                    # handle taking/inventory:
                    # base_result_str = f"You take the {resolution_result[1]}."
                    base_result_str = f"You take the {self.inst_to_type_dict[resolution_result[1]]}."
                    base_result_str += f" {self.get_inventory_desc()}"
                elif len(resolution_result) == 3 and resolution_result[0] == 'at' and resolution_result[1] == 'player1':
                    base_result_str = self.get_full_room_desc()
                else:
                    base_result_str = (f"The {self._get_inst_str(resolution_result[1])} is now {resolution_result[0]} "
                                       f"the {self._get_inst_str(resolution_result[2])}.")
                """
                # check goal achievement:
                # print("goals:", self.goal_state)
                self.goals_achieved = self.goal_state & self.world_state
                goals_achieved_response = list(self.goal_state & self.world_state)
                # print("goals achieved:", self.goals_achieved)
                # convert to goal states to string version:
                for goal_state_idx, goal_state in enumerate(goals_achieved_response):
                    # print("loop goal state:", goal_state)
                    goals_achieved_response[goal_state_idx] = state_tuple_to_str(goal_state)
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
                        for state_pred in self.world_state:
                            if state_pred[0] == 'in' and state_pred[1] == thing:
                                # visible_content_state_strs.append(f"There is a {thing} in the {state_pred[2]}.")
                                # visible_content_state_strs.append(f"There is a {self.inst_to_type_dict[thing]} in the {self.inst_to_type_dict[state_pred[2]]}.")
                                visible_content_state_strs.append(f"There is a {self._get_inst_str(thing)} in the {self._get_inst_str(state_pred[2])}.")
                    visible_content_state_combined = " ".join(visible_content_state_strs)
                    # print("New world state:", self.world_state)
                    return goals_achieved_response, f"{base_result_str} {visible_content_state_combined}"
                else:
                    # print("New world state:", self.world_state)
                    return goals_achieved_response, base_result_str


if __name__ == "__main__":
    PATH = ""

    """
    game_instance_exmpl = {
        "game_id": 0, 
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", 
        "goal_str": "Put a sandwich on the table.", 
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", 
        "initial_state": 
            ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", 
             "closed(refrigerator)",  "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", 
             "in(sandwich,refrigerator)"], 
        "goal_state": ["on(sandwich,table)"]
    }
    
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen)", "type(player1,player)", "at(player1,kitchen)", "type(fridge1,refrigerator)", "at(fridge1,kitchen)",
             "closed(fridge1)",
             "type(fridge2,refrigerator)", "at(fridge2,kitchen)",
             "closed(fridge2)",
             "type(table1,table)", "at(table1,kitchen)", "type(counter1,counter)", "at(counter1,kitchen)", "type(sandwich1,sandwich)", "at(sandwich1,kitchen)",
             "in(sandwich1,fridge1)"],
        "goal_state": ["on(sandwich1,table1)"]
    }
    
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen)", 
             "type(player1,player)", "at(player1,kitchen)",
             "type(fridge1,refrigerator)", "at(fridge1,kitchen)", "closed(fridge1)",
             "type(table1,table)", "at(table1,kitchen)", "adj(table1,wooden)",
             "type(counter1,counter)", "at(counter1,kitchen)",
             "type(sandwich1,sandwich)", "at(sandwich1,kitchen)", "in(sandwich1,fridge1)"],
        "goal_state": ["on(sandwich1,table1)"]
    }
    
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen1,kitchen)", "exit(kitchen1,pantry1)", "exit(kitchen1,hallway1)",
             "room(pantry1,pantry)", "exit(pantry1,kitchen1)",
             "room(hallway1,hallway)", "exit(hallway1,kitchen1)",
             "type(player1,player)", "at(player1,kitchen1)",
             "type(fridge1,refrigerator)", "at(fridge1,kitchen1)", "closed(fridge1)",
             "type(table1,table)", "at(table1,kitchen1)", "adj(table1,wooden)",
             "type(counter1,counter)", "at(counter1,kitchen1)",
             "type(sandwich1,sandwich)", "at(sandwich1,kitchen1)", "in(sandwich1,fridge1)"],
        "goal_state": ["on(sandwich1,table1)"]
    }
    
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen1,kitchen)", "exit(kitchen1,pantry1)",
             "room(pantry1,pantry)", "exit(pantry1,kitchen1)",
             "type(player1,player)", "at(player1,kitchen1)",
             "type(fridge1,refrigerator)", "at(fridge1,kitchen1)", "closed(fridge1)",
             "type(table1,table)", "at(table1,kitchen1)", "adj(table1,wooden)",
             "type(counter1,counter)", "at(counter1,kitchen1)",
             "type(sandwich1,sandwich)", "at(sandwich1,kitchen1)", "in(sandwich1,fridge1)"],
        "goal_state": ["on(sandwich1,table1)"]
    }
    
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen1,kitchen)", "exit(kitchen1,pantry1)", "exit(kitchen1,hallway1)", "exit(kitchen1,livingroom1)",
             "room(pantry1,pantry)", "exit(pantry1,kitchen1)",
             "room(hallway1,hallway)", "exit(hallway1,kitchen1)",
             "room(livingroom1,livingroom)", "exit(livingroom1,kitchen1)",
             "type(player1,player)", "at(player1,kitchen1)",
             "type(fridge1,refrigerator)", "at(fridge1,kitchen1)", "closed(fridge1)",
             "type(table1,table)", "at(table1,kitchen1)", "adj(table1,wooden)",
             "type(counter1,counter)", "at(counter1,kitchen1)",
             "type(sandwich1,sandwich)", "at(sandwich1,kitchen1)", "in(sandwich1,fridge1)",
             "type(apple1,apple)", "at(apple1,kitchen1)"
             ],
        "goal_state": ["at(sandwich1,pantry1)"]
    }
    
    """
    game_instance_exmpl = {
        "game_id": 0,
        "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "goal_str": "Put a sandwich on the table.",
        "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.",
        "initial_state":
            ["room(kitchen1,kitchen)", "exit(kitchen1,pantry1)",
             "room(pantry1,pantry)", "exit(pantry1,kitchen1)",
             "type(player1,player)", "at(player1,kitchen1)",
             "type(fridge1,refrigerator)", "at(fridge1,kitchen1)", "closed(fridge1)", "adj(fridge1,large)",
             "type(table1,table)", "at(table1,kitchen1)", "adj(table1,wooden)",
             "type(counter1,counter)", "at(counter1,kitchen1)",
             "type(sandwich1,sandwich)", "at(sandwich1,kitchen1)", "in(sandwich1,fridge1)",
             "type(apple1,apple)", "at(apple1,kitchen1)"
             ],
        "goal_state": ["at(sandwich1,pantry1)"]
    }

    # game_instance_exmpl = {"game_id": 0, "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "goal_str": "Put a sandwich on the table.", "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "initial_state": ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", "closed(refrigerator)", "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", "in(sandwich,refrigerator)", "in(pomegranate,inventory)"], "goal_state": ["on(sandwich,table)"]}
    # game_instance_exmpl = {"game_id": 0, "prompt": "You are playing a text adventure game. I will describe what you can perceive in the game. You write the action you want to take in the game starting with >.\nFor example:\n> examine cupboard\n\nYour goal for this game is: Put a sandwich on the table.\n\nYou are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "goal_str": "Put a sandwich on the table.", "first_room_str": "You are in the kitchen. There is a refrigerator, a counter and a table. The refrigerator is closed.", "initial_state": ["room(kitchen)", "at(player,kitchen)", "at(refrigerator,kitchen)", "closed(refrigerator)", "at(table,kitchen)", "at(counter,kitchen)", "at(sandwich,kitchen)", "in(sandwich,refrigerator)", "in(pomegranate,inventory)", "in(yoyo,inventory)"], "goal_state": ["on(sandwich,table)"]}

    test_interpreter = BasicIFInterpreter(game_instance_exmpl)

    # print(test_interpreter.action_types)
    # print(test_interpreter.entity_types)

    print(test_interpreter.get_full_room_desc())

    turn_1 = test_interpreter.process_action("open refrigerator")
    print(turn_1[1])
    print()

    # turn_2 = test_interpreter.process_action("take sandwich")
    turn_2 = test_interpreter.process_action("take sandwich from refrigerator")
    # turn_2 = test_interpreter.process_action("take apple")
    print(turn_2[1])
    print()
    """"""
    """
    turn_3 = test_interpreter.process_action("put sandwich on table")
    # turn_3 = test_interpreter.process_action("put sandwich in table")
    # turn_3 = test_interpreter.process_action("place sandwich on table")
    # turn_3 = test_interpreter.process_action("put sandwich on wooden table")
    print(turn_3[1])
    """

    turn_3 = test_interpreter.process_action("go pantry")
    # turn_1 = test_interpreter.process_action("go to pantry")
    # print(turn_3[1])
    print(turn_3)
    """"""
    # print(state_tuple_to_str(('on', 'sandwich1', 'table1')))
