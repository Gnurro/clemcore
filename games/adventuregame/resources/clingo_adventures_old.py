"""
Clingo-based adventure generation and optimal solving.
"""

from typing import List, Tuple, Union, Optional
import json
from itertools import permutations

import numpy as np
from clingo.control import Control
from tqdm import tqdm

from games.adventuregame.adv_util import fact_str_to_tuple, fact_tuple_to_str


# TODO: doc adventure generation config format and contents

class ClingoAdventureBase(object):
    """
    Wraps the clingo ASP module. Base class for adventure generator and adventure solver.
    """
    def __init__(self, adventure_type: str = "home_deliver_two"):
        # initialize clingo controller:
        self.clingo_control: Control = Control(["0"])  # ["0"] argument to return all models

        self.adv_type: str = adventure_type
        # load adventure type definition:
        with open("definitions/adventure_types.json", 'r', encoding='utf-8') as adventure_types_file:
            adventure_type_definitions = json.load(adventure_types_file)
            self.adv_type_def = adventure_type_definitions[self.adv_type]

        # print("adv type:", self.adv_type)
        # print("adv type def:", self.adv_type_def)

        # load room type definitions:
        room_definitions: list = list()
        for room_def_source in self.adv_type_def["room_definitions"]:
            with open(f"definitions/{room_def_source}", 'r', encoding='utf-8') as rooms_file:
                room_definitions += json.load(rooms_file)

        # print(room_definitions)

        self.room_definitions = dict()
        for type_def in room_definitions:
            type_def_dict = dict()
            for type_key, type_value in type_def.items():
                if not type_key == 'type_name':
                    type_def_dict[type_key] = type_value
            self.room_definitions[type_def['type_name']] = type_def_dict

        # print(self.room_definitions)

        # load entity type definitions:
        entity_definitions: list = list()
        for entity_def_source in self.adv_type_def["entity_definitions"]:
            with open(f"definitions/{entity_def_source}", 'r', encoding='utf-8') as entities_file:
                entity_definitions += json.load(entities_file)

        # print(entity_definitions)
        self.entity_definitions = dict()
        for type_def in entity_definitions:
            type_def_dict = dict()
            for type_key, type_value in type_def.items():
                if not type_key == 'type_name':
                    type_def_dict[type_key] = type_value
            self.entity_definitions[type_def['type_name']] = type_def_dict

        # print(self.entity_definitions)

        # load action type definitions:
        action_definitions: list = list()
        for action_def_source in self.adv_type_def["action_definitions"]:
            with open(f"definitions/{action_def_source}", 'r', encoding='utf-8') as actions_file:
                action_definitions += json.load(actions_file)

        # print(room_definitions)

        self.action_definitions = dict()
        for type_def in action_definitions:
            type_def_dict = dict()
            for type_key, type_value in type_def.items():
                if not type_key == 'type_name':
                    type_def_dict[type_key] = type_value
            self.action_definitions[type_def['type_name']] = type_def_dict

        # print(self.room_definitions)
    def reset_clingo_controller(self):
        """
        Resets the clingo controller by initializing a new one.
        """
        self.clingo_control: Control = Control(["0"])  # ["0"] argument to return all models


class ClingoInitialStateGenerator(ClingoAdventureBase):
    """
    Generates initial adventure state sets based on room and entity definitions.
    """
    def __init__(self, adventure_type: str = "home_deliver_two"):
        super().__init__(adventure_type=adventure_type)

    def generate_room_layouts(self, layout_file_path: str = "generated_home_layouts.json"):
        # reset clingo controller:
        self.reset_clingo_controller()

        clingo_str = str()

        # generate with one room each:
        for room_type_name, room_type_values in self.room_definitions.items():
            # basic atoms:
            room_id = f"{room_type_name}1"  # default to 'kitchen1' etc
            # print("room:", room_id)
            type_atom = f"room({room_id},{room_type_name})."
            # add type atom to clingo controller:
            self.clingo_control.add(type_atom)
            clingo_str += "\n" + type_atom

            # add floor to room:
            floor_id = f"{room_id}floor"
            floor_atom = f"type({floor_id},floor)."
            self.clingo_control.add(floor_atom)
            clingo_str += "\n" + floor_atom
            # add at() for room floor:
            floor_at = f"at({floor_id},{room_id})."
            self.clingo_control.add(floor_at)
            clingo_str += "\n" + floor_at
            # add support trait atom for floor:
            floor_support = f"support({floor_id})."
            self.clingo_control.add(floor_support)
            clingo_str += "\n" + floor_support

            # add exit rule:
            permitted_exits_list = list()
            for exit_target in room_type_values['exit_targets']:
                # print(exit_target)
                exit_target_permit = f"exit(ROOM,TARGET):room(ROOM,{room_type_name}),room(TARGET,{exit_target})"
                permitted_exits_list.append(exit_target_permit)
            permitted_exits = ";".join(permitted_exits_list)

            exit_rule = "1 { $PERMITTEDEXITS$ } $MAXCONNECTIONS$."
            # print(exit_rule)
            exit_rule = exit_rule.replace("$PERMITTEDEXITS$", permitted_exits)
            # print(exit_rule)
            exit_rule = exit_rule.replace("$MAXCONNECTIONS$", str(room_type_values['max_connections']))

            # print(exit_rule)
            # add exit rule to clingo controller:
            self.clingo_control.add(exit_rule)
            clingo_str += "\n" + exit_rule
        # add exit pairing rule:
        exit_pairing_rule = "exit(ROOM,TARGET) :- exit(TARGET,ROOM)."
        self.clingo_control.add(exit_pairing_rule)
        clingo_str += "\n" + exit_pairing_rule
        # add rule assuring all rooms are reachable from each other:
        # reachable_rule = "reachable(ROOM,TARGET) :- exit(ROOM,TARGET). reachable(ROOM,TARGET) :- reachable(TARGET,ROOM). reachable(ROOM,TARGET) :- reachable(ROOM,TARGET1), reachable(TARGET1,TARGET), ROOM != TARGET. :- room(ROOM,_), room(TARGET,_), ROOM != TARGET, not reachable(ROOM,TARGET). #hide reachable/2."
        reachable_rule = "reachable(ROOM,TARGET) :- exit(ROOM,TARGET). reachable(ROOM,TARGET) :- reachable(TARGET,ROOM). reachable(ROOM,TARGET) :- reachable(ROOM,TARGET1), reachable(TARGET1,TARGET), ROOM != TARGET. :- room(ROOM,_), room(TARGET,_), ROOM != TARGET, not reachable(ROOM,TARGET)."
        self.clingo_control.add(reachable_rule)
        clingo_str += "\n" + reachable_rule
        # self.clingo_control.add("#hide reachable/2")
        # clingo_str += "\n" + "#hide reachable/2"

        # CLINGO SOLVING
        # ground the combined LP:
        self.clingo_control.ground()
        # print("Grounded!")
        # solve combined LP for room layouts:
        room_layouts = list()

        with self.clingo_control.solve(yield_=True) as solve:
            for model in solve:
                # print("model:", model)
                room_layouts.append(model.__str__())
                # break
            # print("solve get:", solve.get())

        # print(raw_adventures)
        """"""
        # ADVENTURE FORMAT CONVERSION
        result_layouts = list()
        for result_layout in room_layouts:
            fact_list = result_layout.split()
            # remove 'reachable' helper atoms:
            fact_list = [fact for fact in fact_list if "reachable" not in fact]
            result_layouts.append(fact_list)

        # print(result_adventures)

        with open(layout_file_path, 'w', encoding='utf-8') as out_file:
            out_file.write(json.dumps(result_layouts))

        return result_layouts

    def generate_room_layouts_asp(self):
        """
        Generates an ASP encoding string to generate room layouts based on room definitions.
        """
        clingo_str = str()

        # generate with one room each:
        for room_type_name, room_type_values in self.room_definitions.items():
            # basic atoms:
            room_id = f"{room_type_name}1"  # default to 'kitchen1' etc
            # print("room:", room_id)
            type_atom = f"room({room_id},{room_type_name})."
            clingo_str += "\n" + type_atom

            # add floor to room:
            floor_id = f"{room_id}floor"
            floor_atom = f"type({floor_id},floor)."
            clingo_str += "\n" + floor_atom
            # add at() for room floor:
            floor_at = f"at({floor_id},{room_id})."
            clingo_str += "\n" + floor_at
            # add support trait atom for floor:
            floor_support = f"support({floor_id})."
            clingo_str += "\n" + floor_support

            # add exit rule:
            permitted_exits_list = list()
            for exit_target in room_type_values['exit_targets']:
                # print(exit_target)
                exit_target_permit = f"exit(ROOM,TARGET):room(ROOM,{room_type_name}),room(TARGET,{exit_target})"
                permitted_exits_list.append(exit_target_permit)
            permitted_exits = ";".join(permitted_exits_list)

            exit_rule = "1 { $PERMITTEDEXITS$ } $MAXCONNECTIONS$."
            # print(exit_rule)
            exit_rule = exit_rule.replace("$PERMITTEDEXITS$", permitted_exits)
            # print(exit_rule)
            exit_rule = exit_rule.replace("$MAXCONNECTIONS$", str(room_type_values['max_connections']))

            # print(exit_rule)
            clingo_str += "\n" + exit_rule
        # exit pairing rule:
        exit_pairing_rule = "exit(ROOM,TARGET) :- exit(TARGET,ROOM)."
        clingo_str += "\n" + exit_pairing_rule
        # add rule assuring all rooms are reachable from each other:
        # reachable_rule = "reachable(ROOM,TARGET) :- exit(ROOM,TARGET). reachable(ROOM,TARGET) :- reachable(TARGET,ROOM). reachable(ROOM,TARGET) :- reachable(ROOM,TARGET1), reachable(TARGET1,TARGET), ROOM != TARGET. :- room(ROOM,_), room(TARGET,_), ROOM != TARGET, not reachable(ROOM,TARGET). #hide reachable/2."
        reachable_rule = "reachable(ROOM,TARGET) :- exit(ROOM,TARGET). reachable(ROOM,TARGET) :- reachable(TARGET,ROOM). reachable(ROOM,TARGET) :- reachable(ROOM,TARGET1), reachable(TARGET1,TARGET), ROOM != TARGET. :- room(ROOM,_), room(TARGET,_), ROOM != TARGET, not reachable(ROOM,TARGET)."
        clingo_str += "\n" + reachable_rule
        # self.clingo_control.add("#hide reachable/2")
        # clingo_str += "\n" + "#hide reachable/2"

        return clingo_str

    def process_room_layout_clingo_model(self, room_layout_str: str) -> List[str]:
        """
        Process room layout clingo model string to list of fact strings.
        """
        fact_list = room_layout_str.split()
        # remove 'reachable' helper atoms:
        fact_list = [fact for fact in fact_list if "reachable" not in fact]
        return fact_list

    def generate_initial_states(self, layout_file_path: str = "generated_home_layouts.json",
                                initial_state_file_path: str = "generated_home_initial_states.jsonl"):
        # reset clingo controller:
        self.reset_clingo_controller()

        # load room layouts:
        with open(layout_file_path, 'r', encoding='utf-8') as layout_file:
            room_layouts = json.load(layout_file)

        # print(room_layouts)
        layout_count = len(room_layouts)

        clingo_str = str()

        for rooms_layout in tqdm(room_layouts):
            # reset clingo controller:
            self.reset_clingo_controller()
            # convert/add room layout facts:
            cur_layout = "\n".join([fact + "." for fact in rooms_layout])
            # print(cur_layout)
            self.clingo_control.add(cur_layout)

            # add player type fact:
            player_fact = "type(player1,player)."
            self.clingo_control.add(player_fact)
            clingo_str += "\n" + player_fact
            # add rule for random player start location:
            player_location_rule = "1 { at(player1,ROOM):room(ROOM,_) } 1."
            self.clingo_control.add(player_location_rule)
            clingo_str += "\n" + player_location_rule

            for entity_type_name, entity_type_values in self.entity_definitions.items():
                if "standard_locations" in entity_type_values:
                    # basic atoms:
                    entity_id = f"{entity_type_name}1"  # default to 'kitchen1' etc
                    # print("room:", room_id)
                    type_atom = f"type({entity_id},{entity_type_name})."
                    # add type atom to clingo controller:
                    self.clingo_control.add(type_atom)
                    clingo_str += "\n" + type_atom
                    # location rule:
                    permitted_location_list = list()

                    for location in entity_type_values['standard_locations']:
                        permitted_location = f"at(ENTITY,ROOM):type(ENTITY,{entity_type_name}),room(ROOM,{location})"
                        permitted_location_list.append(permitted_location)
                    permitted_locations_str = ";".join(permitted_location_list)

                    location_rule = "1 { $PERMITTEDLOCATIONS$ } 1."
                    location_rule = location_rule.replace("$PERMITTEDLOCATIONS$", permitted_locations_str)
                    # print(location_rule)
                    self.clingo_control.add(location_rule)
                    clingo_str += "\n" + location_rule

                    if "traits" in entity_type_values:
                        # add atoms for all traits of this entity type:
                        for trait in entity_type_values['traits']:
                            trait_atom = f"{trait}({entity_id})."
                            self.clingo_control.add(trait_atom)
                            clingo_str += "\n" + trait_atom

                        if "needs_support" in entity_type_values['traits']:
                            # on/in rule:
                            on_positions = "on(entity_id,SUPPORT):at(entity_id,ROOM),at(SUPPORT,ROOM),support(SUPPORT);"
                            in_positions = "in(entity_id,SUPPORT):at(entity_id,ROOM),at(CONTAINER,ROOM),container(CONTAINER)"
                            # support_rule = "1 { on(ENTITY,SUPPORT):at(ENTITY,ROOM),at(SUPPORT,ROOM),support(SUPPORT);in(ENTITY,CONTAINER):at(ENTITY,ROOM),at(CONTAINER,ROOM),container(CONTAINER) } 1."
                            # support_rule = "1 { on($ENTITY$,SUPPORT):at($ENTITY$,ROOM),at(SUPPORT,ROOM),support(SUPPORT);in($ENTITY$,CONTAINER):at($ENTITY$,ROOM),at(CONTAINER,ROOM),container(CONTAINER) } 1."
                            support_rule = "1 { on($ENTITY$,SUPPORT):at($ENTITY$,ROOM),at(SUPPORT,ROOM),support(SUPPORT);in($ENTITY$,CONTAINER):at($ENTITY$,ROOM),at(CONTAINER,ROOM),container(CONTAINER) } 1."
                            support_rule = support_rule.replace("$ENTITY$", entity_id)
                            # support_rule = "1 { "
                            # support_rule += on_positions
                            # support_rule += in_positions
                            # support_rule += " } 1."
                            # print(support_rule)
                            self.clingo_control.add(support_rule)
                            clingo_str += "\n" + support_rule

                        if "openable" in entity_type_values['traits']:
                            closed_atom = f"closed({entity_id})."
                            self.clingo_control.add(closed_atom)
                            clingo_str += "\n" + closed_atom

                    if not self.adv_type_def['initial_state_config']["entity_adjectives"] == "none":
                        if "possible_adjs" in entity_type_values:
                            # adjective rule:
                            possible_adj_list = list()
                            for possible_adj in entity_type_values["possible_adjs"]:
                                possible_adj_str = f"adj({entity_id},{possible_adj})"
                                possible_adj_list.append(possible_adj_str)
                            possible_adjs = ";".join(possible_adj_list)
                            if self.adv_type_def['initial_state_config']["entity_adjectives"] == "optional":
                                adj_rule = "0 { $POSSIBLEADJS$ } 1."
                            elif self.adv_type_def['initial_state_config']["entity_adjectives"] == "all":
                                adj_rule = "1 { $POSSIBLEADJS$ } 1."
                            adj_rule = adj_rule.replace("$POSSIBLEADJS$", possible_adjs)
                            self.clingo_control.add(adj_rule)
                            clingo_str += "\n" + adj_rule

                            # make sure that same-type entities do not have same adjective:
                            diff_adj_rule = ":- adj(ENTITY1,ADJ), adj(ENTITY2,ADJ), type(ENTITY1,TYPE), type(ENTITY2,TYPE), ENTITY1 != ENTITY2."
                            self.clingo_control.add(diff_adj_rule)
                            clingo_str += "\n" + diff_adj_rule

            # print(clingo_str)

            # CLINGO SOLVING
            # ground the combined LP:
            self.clingo_control.ground()
            # print("Grounded!")
            # solve combined LP for raw adventures:
            raw_adventures = list()

            with self.clingo_control.solve(yield_=True) as solve:
                with open(initial_state_file_path, 'a', encoding='utf-8') as out_file:
                    for model in solve:
                        # print("model:", model)
                        # raw_adventures.append(model.__str__())
                        raw_adventure = model.__str__()
                        fact_list = raw_adventure.split()
                        out_file.write(json.dumps(fact_list) + "\n")
                        # break
                    # print("solve get:", solve.get())

            # print(raw_adventures)
            """
            # ADVENTURE FORMAT CONVERSION
            result_adventures = list()
            for raw_adventure in raw_adventures:
                fact_list = raw_adventure.split()
                # remove 'reachable' helper atoms:
                fact_list = [fact for fact in fact_list if "reachable" not in fact]
                result_adventures.append(fact_list)

            # print(result_adventures)

            with open(initial_state_file_path, 'a', encoding='utf-8') as out_file:
                out_file.write(json.dumps(result_adventures))

        return result_adventures
        """

    def generate_initial_states_asp(self, room_layout_facts: list):
        """
        Generates an ASP encoding string to generate initial world states based on a room layout and entity definitions.
        """
        clingo_str = str()

        # convert/add room layout facts:
        cur_layout = "\n".join([fact + "." for fact in room_layout_facts])
        # print(cur_layout)
        clingo_str += cur_layout

        # add player type fact:
        player_fact = "type(player1,player)."
        clingo_str += "\n" + player_fact
        # add rule for random player start location:
        player_location_rule = "1 { at(player1,ROOM):room(ROOM,_) } 1."
        clingo_str += "\n" + player_location_rule

        for entity_type_name, entity_type_values in self.entity_definitions.items():
            if "standard_locations" in entity_type_values:
                # basic atoms:
                entity_id = f"{entity_type_name}1"  # default to 'kitchen1' etc
                # print("room:", room_id)
                type_atom = f"type({entity_id},{entity_type_name})."
                # add type atom to asp encoding:
                clingo_str += "\n" + type_atom
                # location rule:
                permitted_location_list = list()

                for location in entity_type_values['standard_locations']:
                    permitted_location = f"at(ENTITY,ROOM):type(ENTITY,{entity_type_name}),room(ROOM,{location})"
                    permitted_location_list.append(permitted_location)
                permitted_locations_str = ";".join(permitted_location_list)

                location_rule = "1 { $PERMITTEDLOCATIONS$ } 1."
                location_rule = location_rule.replace("$PERMITTEDLOCATIONS$", permitted_locations_str)
                # print(location_rule)
                clingo_str += "\n" + location_rule

                if "traits" in entity_type_values:
                    # add atoms for all traits of this entity type:
                    for trait in entity_type_values['traits']:
                        trait_atom = f"{trait}({entity_id})."
                        clingo_str += "\n" + trait_atom

                    if "needs_support" in entity_type_values['traits']:
                        # on/in rule:
                        support_rule = "1 { on($ENTITY$,SUPPORT):at($ENTITY$,ROOM),at(SUPPORT,ROOM),support(SUPPORT);in($ENTITY$,CONTAINER):at($ENTITY$,ROOM),at(CONTAINER,ROOM),container(CONTAINER) } 1."
                        support_rule = support_rule.replace("$ENTITY$", entity_id)
                        # print(support_rule)
                        clingo_str += "\n" + support_rule

                    if "openable" in entity_type_values['traits']:
                        closed_atom = f"closed({entity_id})."
                        clingo_str += "\n" + closed_atom

                if not self.adv_type_def['initial_state_config']["entity_adjectives"] == "none":
                    if "possible_adjs" in entity_type_values:
                        # adjective rule:
                        possible_adj_list = list()
                        for possible_adj in entity_type_values["possible_adjs"]:
                            possible_adj_str = f"adj({entity_id},{possible_adj})"
                            possible_adj_list.append(possible_adj_str)
                        possible_adjs = ";".join(possible_adj_list)
                        if self.adv_type_def['initial_state_config']["entity_adjectives"] == "optional":
                            adj_rule = "0 { $POSSIBLEADJS$ } 1."
                        elif self.adv_type_def['initial_state_config']["entity_adjectives"] == "all":
                            adj_rule = "1 { $POSSIBLEADJS$ } 1."
                        adj_rule = adj_rule.replace("$POSSIBLEADJS$", possible_adjs)
                        clingo_str += "\n" + adj_rule

                        # make sure that same-type entities do not have same adjective:
                        diff_adj_rule = ":- adj(ENTITY1,ADJ), adj(ENTITY2,ADJ), type(ENTITY1,TYPE), type(ENTITY2,TYPE), ENTITY1 != ENTITY2."
                        clingo_str += "\n" + diff_adj_rule

        # print(clingo_str)

        return clingo_str


class ClingoGoalGenerator(ClingoAdventureBase):
    """
    Generate goals for adventures, based on initial world states.
    NOTE: Technically does not use clingo currently, but other tasks than 'deliver' might use it.
    """
    def __init__(self, adventure_type: str = "home_deliver_two", rng_seed: int = 42):
        super().__init__(adventure_type=adventure_type)
        self.goal_yield_counter = -1
        self.rng = np.random.default_rng(seed=rng_seed)

    def initialize_adventure_state(self, initial_world_state):
        """
        Set up initial world state and add facts to clingo controller.
        Turn facts have _t in the fact/atom type, and their first value is the turn at which they are true.
        """
        self.id_to_type_dict: dict = dict()

        # convert fact strings to tuples:
        self.initial_facts = [fact_str_to_tuple(fact) for fact in initial_world_state]
        # iterate over initial world state, add fixed basic facts, add turn facts for changeable facts
        for fact in self.initial_facts:
            # print("initial fact:", fact)
            if fact[0] == "type":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.entity_definitions[fact[2]]['repr_str']}
                if 'traits' in self.entity_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.entity_definitions[fact[2]]['traits']
            if fact[0] == "room":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.room_definitions[fact[2]]['repr_str']}
                if 'traits' in self.room_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.room_definitions[fact[2]]['traits']

    def generate_goal_facts(self, initial_world_state):
        """
        Generate goal facts based on task type and given adventure initial world state.
        Task types:
            'deliver': Bring takeable objects to support or container; goal facts are of type 'on' or 'in'.
        """
        # initialize adventure world state:
        self.initialize_adventure_state(initial_world_state)

        task_config = self.adv_type_def['task_config']
        goal_count = self.adv_type_def['goal_count']

        if task_config['task'] == "deliver":
            # get initial in/on of takeables:
            takeables: dict = dict()
            holders: dict = dict()
            for fact in self.initial_facts:
                if fact[0] == "takeable":
                    # print(fact)
                    if fact[1] not in takeables:
                        takeables[fact[1]] = {'type': self.id_to_type_dict[fact[1]]['type']}
                    else:
                        takeables[fact[1]]['type'] = self.id_to_type_dict[fact[1]]['type']
                if fact[0] in ["on", "in"]:
                    # print(fact)
                    if fact[1] not in takeables:
                        takeables[fact[1]] = {'state': fact[0], 'holder': fact[2]}
                    else:
                        takeables[fact[1]]['state'] = fact[0]
                        takeables[fact[1]]['holder'] = fact[2]
                if fact[0] in ["container", "support"]:
                    # print(fact)
                    if fact[1] not in holders:
                        holders[fact[1]] = {'type': self.id_to_type_dict[fact[1]]['type'], 'holder_type': fact[0]}
                    else:
                        holders[fact[1]]['type'] = self.id_to_type_dict[fact[1]]['type']
                        holders[fact[1]]['holder_type'] = fact[0]

            if not task_config['deliver_to_floor']:
                bad_holders: list = list()
                for holder, holder_values in holders.items():
                    if holder_values['type'] == "floor":
                        bad_holders.append(holder)
                for bad_holder in bad_holders:
                    del holders[bad_holder]

            # print(takeables)
            # print(holders)

            possible_destinations: dict = dict()

            for takeable, takeable_values in takeables.items():
                # print(takeable)
                for holder, holder_values in holders.items():
                    if not takeable_values['holder'] == holder:
                        # print(holder)
                        if takeable not in possible_destinations:
                            possible_destinations[takeable] = [holder]
                        else:
                            possible_destinations[takeable].append(holder)

            # print(possible_destinations)

            all_possible_goals: list = list()
            for takeable, destinations in possible_destinations.items():
                for destination in destinations:
                    # if self.id_to_type_dict[destination]['holder_type'] == "container":
                    if holders[destination]['holder_type'] == "container":
                        pred_type = "in"
                    # elif self.id_to_type_dict[destination]['holder_type'] == "support":
                    elif holders[destination]['holder_type'] == "support":
                        pred_type = "on"
                    goal_str: str = f"{pred_type}({takeable},{destination})"
                    all_possible_goals.append(goal_str)
            # print(all_possible_goals)

            self.goal_combos = list(permutations(all_possible_goals, goal_count))
            # print(self.goal_combos)

    def get_goals_iter(self):
        """
        Generator method to iteratively get generated goal combos.
        """
        assert self.goal_combos, "No goal combos have been generated, please run .generate_goal_facts() first."
        self.goal_yield_counter += 1
        yield list(self.goal_combos[self.goal_yield_counter])

    def get_goals_random(self, amount: int = 1, replace: bool = False):
        """
        Get a specified number of random goal combos, by default does not return the same combo multiple times.
        """
        assert self.goal_combos, "No goal combos have been generated, please run .generate_goal_facts() first."
        choice_list = self.rng.choice(self.goal_combos, size=amount, replace=replace, shuffle=False).tolist()
        return choice_list


class ClingoAdventureSolver(ClingoAdventureBase):
    """
    Solves adventure with given goal states, optimizing action sequence.
    """
    def __init__(self, adventure_type: str = "home_deliver_two"):
        super().__init__(adventure_type=adventure_type)

        # load clingo ASP templates:
        with open("clingo_templates.json", 'r', encoding='utf-8') as templates_file:
            self.clingo_templates = json.load(templates_file)

    def convert_actions(self):
        """
        Convert action definitions into ASP rules.
        """
        # NOTE: this has not been implemented due to time constraints
        # ASP encodings have been developed more directly and are simply stored in the action definition JSON
        # time permitting, the state change definitions of action will be overhauled to be more directly usable for ASP
        # as well as for the IF interpreter
        for action_name, action_def in self.action_definitions.items():
            print(action_name)
            # print(action_def['state_changes'])
            for change_idx, state_change in enumerate(action_def['state_changes']):
                if change_idx == 0:
                    # print("first state change:", state_change)
                    action_t_template = "{ action_t(TURN,$ACTIONTYPE$,THING):at_t(TURN,THING,ROOM),$PRESTATE$_t(TURN,THING) } 1 :- turn(TURN), at_t(TURN,player1,ROOM), not turn_limit(TURN)."
                    action_t_rule = action_t_template.replace("$ACTIONTYPE$", action_name)
                    prestate_tuple = fact_str_to_tuple(state_change["pre_state"])
                    action_t_rule = action_t_rule.replace("$PRESTATE$", prestate_tuple[0])
                    print(action_t_rule)
            # break

    def initialize_adventure_turns(self, initial_world_state, return_encoding: bool = False):
        """
        Set up initial world state and add facts to clingo controller.
        Turn facts have _t in the fact/atom type, and their first value is the turn at which they are true.
        """
        mutable_fact_types: list = self.adv_type_def["mutable_fact_types"]

        if return_encoding:
            clingo_str = str()

        self.id_to_type_dict: dict = dict()

        # convert fact strings to tuples:
        self.initial_facts = [fact_str_to_tuple(fact) for fact in initial_world_state]
        # iterate over initial world state, add fixed basic facts, add turn facts for changeable facts
        for fact in self.initial_facts:
            # print("initial fact:", fact)
            # set up id_to_type:
            if fact[0] == "type":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.entity_definitions[fact[2]]['repr_str']}
                if 'traits' in self.entity_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.entity_definitions[fact[2]]['traits']
            if fact[0] == "room":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.room_definitions[fact[2]]['repr_str']}
                if 'traits' in self.room_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.room_definitions[fact[2]]['traits']
            # set up per-turn mutable facts at turn 0:
            if fact[0] in mutable_fact_types:
                # add turn 0 turn fact atom:
                if len(fact) == 3:
                    turn_atom = f"{fact[0]}_t(0,{fact[1]},{fact[2]})."
                    self.clingo_control.add(turn_atom)
                    if return_encoding:
                        clingo_str += "\n" + turn_atom
                if len(fact) == 2:
                    turn_atom = f"{fact[0]}_t(0,{fact[1]})."
                    self.clingo_control.add(turn_atom)
                    if return_encoding:
                        clingo_str += "\n" + turn_atom
            else:
                # add constant fact atom:
                const_atom = f"{fact_tuple_to_str(fact)}."
                self.clingo_control.add(const_atom)
                if return_encoding:
                    clingo_str += "\n" + const_atom

        # print(self.id_to_type_dict)

        if return_encoding:
            return clingo_str

    def initialize_adventure_turns_asp(self, initial_world_state):
        """
        Set up initial world state and create ASP encoding of mutable facts.
        Turn facts have _t in the fact/atom type, and their first value is the turn at which they are true.
        """
        mutable_fact_types: list = self.adv_type_def["mutable_fact_types"]

        clingo_str = str()

        self.id_to_type_dict: dict = dict()

        # convert fact strings to tuples:
        self.initial_facts = [fact_str_to_tuple(fact) for fact in initial_world_state]
        # iterate over initial world state, add fixed basic facts, add turn facts for changeable facts
        for fact in self.initial_facts:
            # print("initial fact:", fact)
            # set up id_to_type:
            if fact[0] == "type":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.entity_definitions[fact[2]]['repr_str']}
                if 'traits' in self.entity_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.entity_definitions[fact[2]]['traits']
            if fact[0] == "room":
                self.id_to_type_dict[fact[1]] = {'type': fact[2],
                                                 'repr_str': self.room_definitions[fact[2]]['repr_str']}
                if 'traits' in self.room_definitions[fact[2]]:
                    self.id_to_type_dict[fact[1]]['traits'] = self.room_definitions[fact[2]]['traits']
            # set up per-turn mutable facts at turn 0:
            if fact[0] in mutable_fact_types:
                # add turn 0 turn fact atom:
                if len(fact) == 3:
                    turn_atom = f"{fact[0]}_t(0,{fact[1]},{fact[2]})."
                    clingo_str += "\n" + turn_atom
                if len(fact) == 2:
                    turn_atom = f"{fact[0]}_t(0,{fact[1]})."
                    clingo_str += "\n" + turn_atom
            else:
                # add constant fact atom:
                const_atom = f"{fact_tuple_to_str(fact)}."
                clingo_str += "\n" + const_atom

        # print(self.id_to_type_dict)

        return clingo_str

    def solve_optimally(self, initial_world_state, goal_facts: list,
                        return_only_actions: bool = True, return_only_optimal: bool = True,
                        return_encoding: bool = False) -> Tuple[bool, Union[List[str], List[List[str]]], Optional[str]]:
        """
        Generates an optimized solution to an adventure.
        :param initial_world_state: Initial world state fact list.
        :param goal_facts: List of goal facts in string format, ie 'on(sandwich1,table1)'.
        :param turn_limit: Limit number of turns/actions to solve adventure. NOTE: Main factor for solvability.
        :param return_only_actions: Return only a list of action-at-turn atoms. If False, ALL model atoms are returned.
        :param return_only_optimal: Return only the optimal solution model's atoms.
        :param return_encoding: Return the entire adventure solving ASP encoding generated.
        :return: Tuple of: Solvability, list of solution models or optimal solution model, ASP solving encoding.
        """

        turn_limit: int = self.adv_type_def["optimal_solver_turn_limit"]

        if return_encoding:
            clingo_str = str()

        # add turn generation and limit first:
        turns_template: str = self.clingo_templates["turns"]
        turns_clingo = turns_template.replace("$TURNLIMIT$", str(turn_limit))
        self.clingo_control.add(turns_clingo)
        if return_encoding:
            clingo_str += "\n" + turns_clingo

        # add initial world state facts:
        if return_encoding:
            initial_state_clingo = self.initialize_adventure_turns(initial_world_state, return_encoding=True)
            clingo_str += "\n" + initial_state_clingo
        else:
            self.initialize_adventure_turns(initial_world_state)

        # add actions:
        for action_name, action_def in self.action_definitions.items():
            action_asp = action_def['asp']
            self.clingo_control.add(action_asp)
            if return_encoding:
                clingo_str += "\n" + action_asp

        # add action/turn restraints:
        actions_turns_clingo: str = self.clingo_templates["action_limits"]
        self.clingo_control.add(actions_turns_clingo)
        if return_encoding:
            clingo_str += "\n" + actions_turns_clingo

        # print("goal set", goal_facts)

        # add goals:
        for goal in goal_facts:
            # print("goal fact:", goal)
            goal_tuple = fact_str_to_tuple(goal)
            if len(goal_tuple) == 2:
                goal_template: str = self.clingo_templates["goal_1"]
                goal_clingo = goal_template.replace("$PREDICATE$", goal_tuple[0])
                goal_clingo = goal_clingo.replace("$THING$", goal_tuple[1])
            if len(goal_tuple) == 3:
                goal_template: str = self.clingo_templates["goal_2"]
                goal_clingo = goal_template.replace("$PREDICATE$", goal_tuple[0])
                goal_clingo = goal_clingo.replace("$THING$", goal_tuple[1])
                goal_clingo = goal_clingo.replace("$TARGET$", goal_tuple[2])
            self.clingo_control.add(goal_clingo)
            if return_encoding:
                clingo_str += "\n" + goal_clingo

        # add optimization:
        minimize_clingo = self.clingo_templates["minimize"]
        self.clingo_control.add(minimize_clingo)
        if return_encoding:
            clingo_str += "\n" + minimize_clingo

        # add output only actions:
        if return_only_actions:
            only_actions_clingo = self.clingo_templates["return_only_actions"]
            self.clingo_control.add(only_actions_clingo)
            if return_encoding:
                clingo_str += "\n" + only_actions_clingo

        # ground and solve:
        self.clingo_control.ground()
        # solve combined LP for raw solutions:
        raw_solutions = list()

        with self.clingo_control.solve(yield_=True) as solve:
            for model in solve:
                raw_solutions.append(model.__str__())
            # satisfiable = solve.get()
            satisfiable = str(solve.get())
            if satisfiable == "SAT":
                solvable = True
            elif satisfiable == "UNSAT":
                solvable = False

        if return_only_optimal and raw_solutions:
            raw_solutions = raw_solutions[-1]

        if return_encoding:
            return solvable, raw_solutions, clingo_str
        else:
            return solvable, raw_solutions

    def solve_optimally_asp(self, initial_world_state, goal_facts: list,
                        return_only_actions: bool = True, return_only_optimal: bool = True,
                        ) -> Tuple[bool, Union[List[str], List[List[str]]], Optional[str]]:
        """
        Generates an optimized solution to an adventure.
        :param initial_world_state: Initial world state fact list.
        :param goal_facts: List of goal facts in string format, ie 'on(sandwich1,table1)'.
        :param turn_limit: Limit number of turns/actions to solve adventure. NOTE: Main factor for solvability.
        :param return_only_actions: Return only a list of action-at-turn atoms. If False, ALL model atoms are returned.
        :param return_only_optimal: Return only the optimal solution model's atoms.
        :param return_encoding: Return the entire adventure solving ASP encoding generated.
        :return: Tuple of: Solvability, list of solution models or optimal solution model, ASP solving encoding.
        """

        turn_limit: int = self.adv_type_def["optimal_solver_turn_limit"]

        clingo_str = str()

        # add turn generation and limit first:
        turns_template: str = self.clingo_templates["turns"]
        turns_clingo = turns_template.replace("$TURNLIMIT$", str(turn_limit))
        clingo_str += "\n" + turns_clingo

        # add initial world state facts:
        initial_state_clingo = self.initialize_adventure_turns(initial_world_state, return_encoding=True)
        clingo_str += "\n" + initial_state_clingo

        # add actions:
        for action_name, action_def in self.action_definitions.items():
            action_asp = action_def['asp']
            clingo_str += "\n" + action_asp

        # add action/turn restraints:
        actions_turns_clingo: str = self.clingo_templates["action_limits"]
        clingo_str += "\n" + actions_turns_clingo

        # print("goal set", goal_facts)

        # add goals:
        for goal in goal_facts:
            # print("goal fact:", goal)
            goal_tuple = fact_str_to_tuple(goal)
            if len(goal_tuple) == 2:
                goal_template: str = self.clingo_templates["goal_1"]
                goal_clingo = goal_template.replace("$PREDICATE$", goal_tuple[0])
                goal_clingo = goal_clingo.replace("$THING$", goal_tuple[1])
            if len(goal_tuple) == 3:
                goal_template: str = self.clingo_templates["goal_2"]
                goal_clingo = goal_template.replace("$PREDICATE$", goal_tuple[0])
                goal_clingo = goal_clingo.replace("$THING$", goal_tuple[1])
                goal_clingo = goal_clingo.replace("$TARGET$", goal_tuple[2])
            clingo_str += "\n" + goal_clingo

        # add optimization:
        minimize_clingo = self.clingo_templates["minimize"]
        clingo_str += "\n" + minimize_clingo

        # add output only actions:
        if return_only_actions:
            only_actions_clingo = self.clingo_templates["return_only_actions"]
            clingo_str += "\n" + only_actions_clingo

        return clingo_str

    def convert_adventure_solution(self, adventure_solution: str):
        """
        Convert a raw solution string into list of IF commands and get additional information. Expects only-actions raw
        string from ClingoAdventureSolver.
        """
        # print("adventure solution to convert:", adventure_solution)
        actions_list: list = adventure_solution.split()
        action_tuples = [convert_action_to_tuple(action) for action in actions_list]
        action_tuples.sort(key=lambda turn: turn[0])
        # print("sorted action tuples:", action_tuples)
        # TODO: handle adjectives; use adj facts in self.initial_state
        actions_abstract: list = list()
        action_commands: list = list()
        for action_tuple in action_tuples:
            if len(action_tuple) == 3:
                command: str = f"{action_tuple[1]} {self.id_to_type_dict[action_tuple[2]]['repr_str']}"
                abstract_action = [action_tuple[1], action_tuple[2]]
            if len(action_tuple) == 4:
                # TODO?: extract this to action def?
                if action_tuple[1] == "put":
                    if "support" in self.id_to_type_dict[action_tuple[3]]['traits']:
                        command: str = (f"{action_tuple[1]} {self.id_to_type_dict[action_tuple[2]]['repr_str']} "
                                        f"on {self.id_to_type_dict[action_tuple[3]]['repr_str']}")
                    if "container" in self.id_to_type_dict[action_tuple[3]]['traits']:
                        command: str = (f"{action_tuple[1]} {self.id_to_type_dict[action_tuple[2]]['repr_str']} "
                                        f"in {self.id_to_type_dict[action_tuple[3]]['repr_str']}")
                else:
                    command: str = (f"{action_tuple[1]} {self.id_to_type_dict[action_tuple[2]]['repr_str']} "
                                    f"{self.id_to_type_dict[action_tuple[3]]['repr_str']}")
                abstract_action = [action_tuple[1], action_tuple[2], action_tuple[3]]
            action_commands.append(command)
            actions_abstract.append(abstract_action)
        # print(action_commands)
        # print("abstract actions:", actions_abstract)
        return actions_abstract, len(action_tuples), action_commands


def convert_action_to_tuple(action: str):
    action_splice = action[9:-1]
    action_split = action_splice.split(",")
    action_split[0] = int(action_split[0])
    action_tuple = tuple(action_split)
    return action_tuple


class ClingoAdventureGenerator(ClingoAdventureBase):
    """
    Generates full adventures (initial state and goals), solves each to check optimal number of turns.
    """
    def __init__(self, adventure_type: str = "home_deliver_two", rng_seed: int = 42):
        super().__init__(adventure_type=adventure_type)
        self.rng_seed = rng_seed
        self.rng = np.random.default_rng(seed=self.rng_seed)

        self.initial_state_generator: ClingoInitialStateGenerator = ClingoInitialStateGenerator(
            adventure_type=self.adv_type)
        self.initial_states: list = list()

        # self.goal_generator: ClingoGoalGenerator = ClingoGoalGenerator()
        # self.adventure_solver: ClingoAdventureSolver = ClingoAdventureSolver()

    def _generate_initial_states(self):
        """
        Generate initial adventure world states.
        Currently relies on hardcoded default settings, config yet to be implemented.
        """
        self.initial_states = self.initial_state_generator.generate_initial_states()

    def _load_initial_states_from_file(self, initial_states_file_path: str):
        """
        Load pre-generated initial adventure world states from file.
        """
        with open(initial_states_file_path, 'r', encoding='utf-8') as initial_states_file:
            self.initial_states = json.load(initial_states_file)
        print(f"Initial states loaded from {initial_states_file_path}.")

    def _generate_goals(self, initial_state: list, task_config: dict,
                        goal_set_limit: int = 0, goal_set_picking: str = "iterate"):
        """
        Generate goals for an initial state.
        :param initial_state:
        :param task_config: Task configuration; currently only 'deliver' exists.
        :param goals_per_adventure: How many goal facts each adventure has.
        :param goal_set_limit: How many goals sets for different adventures with the same initial state to generate.
            If 0 (default), ALL possible permutations of goal facts of size goals_per_adventure are generated.
        :param goal_set_picking: Method to pick from all possible goal states:
            "iterate" - Picks goal sets from the first permutation iteratively until goal_set_limit is reached.
            "random" - Picks random goal sets from all permutations until goal_set_limit is reached.
        """

        goals_per_adventure: int = self.adv_type_def["goal_count"]

        goal_generator = ClingoGoalGenerator(adventure_type=self.adv_type, rng_seed=self.rng_seed)
        if not task_config:
            task_config = {'task': "deliver", 'deliver_to_floor': False}
        goal_generator.generate_goal_facts(initial_state, task_config, goals_per_adventure)

        if goal_set_picking == "iterative":
            if goal_set_limit:
                goal_sets = [next(goal_generator.get_goals_iter()) for goal_set in range(goal_set_limit)]
            else:
                goal_sets = goal_generator.goal_combos

        elif goal_set_picking == "random":
            assert goal_set_limit > 0, ("Random goal set picking without a limit is equivalent to getting all sets "
                                        "iteratively.")
            goal_sets = goal_generator.get_goals_random(amount=goal_set_limit)

        return goal_sets

    def _solve_adventure(self, adventure_core: dict, turn_limit: int = 50):
        """
        Solve an adventure to get optimal solution, with action sequence and turn count.
        :param adventure_core: Dict with initial state and goals.
        """
        adventure_solver = ClingoAdventureSolver(adventure_type=self.adv_type)

        # solvable, solution = adventure_solver.solve_optimally(adventure_core['initial_state'], adventure_core['goals'], turn_limit=turn_limit)
        solvable, solution = adventure_solver.solve_optimally(adventure_core['initial_state'], adventure_core['goals'])
        """
        solvable, solution, encoding = adventure_solver.solve_optimally(
            adventure_core['initial_state'], adventure_core['goals'], turn_limit=turn_limit, return_encoding=True)

        print(encoding)
        """
        if solvable:
            # action_sequence, optimal_turns = adventure_solver.convert_adventure_solution(solution)
            action_sequence, optimal_turns, command_sequence = adventure_solver.convert_adventure_solution(solution)
            return solvable, action_sequence, optimal_turns, command_sequence
        else:
            return solvable, [], 0, []

    def generate_adventures(self,
                            load_initial_states_from_file: str = "",
                            initial_state_limit: int = 0, initial_state_picking: str = "iterative",
                            adventures_per_initial_state: int = 0,
                            goal_set_picking: str = "iterative",
                            save_to_file: bool = True, indent_output_json: bool = True):
        """
        Generate adventures based on parameters.
        The total number of adventures generated is initial_state_limit * adventures_per_initial_state - if both are 0,
        a very large number of adventures will be generated. All 1-object-per-type, non-adjective basic/house initial
        states already number over 240k, so these values should be limited. Use RNG seeds to reproduce smaller sets of
        adventures that have been picked randomly.
        :param task_config: Task configuration, currently only 'deliver' exists. (Might also determine initial state
            generation in the future.)
        :param load_initial_states_from_file: If a file path is passed, pre-generated initial states are loaded,
            otherwise all possible initial states are generated.
        :param initial_state_limit: The maximum number of initial states to generate adventures for. If 0 (default), ALL
            available initial states will be used.
        :param initial_state_picking: Method to pick from all possible goal states:
            "iterate" - Picks initial states from the first available iteratively until initial_state_limit is reached.
            "random" - Picks random initial states from all available until initial_state_limit is reached.
        :param adventures_per_initial_state: How many adventures to generate for each initial state.
        :param goals_per_adventure: How many goals each adventure has.
        :param goal_set_picking: Method to pick from all possible goal states:
            "iterate" - Picks goal sets from the first permutation iteratively until goals_per_adventure is met.
            "random" - Picks random goal sets from all permutations until goals_per_adventure is met.
        :param turn_limit: Maximum number of turns that optimal solution generator can take.
        :param min_optimal_turns: Adventures that need less than this number of turns to solve will be discarded.
        :param max_optimal_turns: Adventures that need more than this number of turns to solve will be discarded.
        :param save_to_file: File name for saving generated adventures. If empty string, generated adventures will not
            be saved.
        """

        task_config: dict = self.adv_type_def["task_config"]

        goals_per_adventure: int = self.adv_type_def["goal_count"]

        turn_limit: int = self.adv_type_def["optimal_solver_turn_limit"]
        min_optimal_turns: int = self.adv_type_def["min_optimal_turns"]
        max_optimal_turns: int = self.adv_type_def["max_optimal_turns"]

        # set up initial states:
        if load_initial_states_from_file:
            self._load_initial_states_from_file(load_initial_states_from_file)
        else:
            self._generate_initial_states()

        # get initial states to generate adventures with:
        if initial_state_picking == "iterative":
            if initial_state_limit:
                initial_states_used = [self.initial_states[idx] for idx in range(initial_state_limit)]
            else:
                initial_states_used = self.initial_states
        elif initial_state_picking == "random":
            assert initial_state_limit > 0, ("Random initial state picking without a limit is equivalent to getting all"
                                             " iteratively.")
            # initial_states_used = self.rng.choice(self.initial_states, size=initial_state_limit, replace=False, shuffle=False).tolist()
            # print(type(self.initial_states))
            initial_state_indices = self.rng.choice(len(self.initial_states), size=initial_state_limit, replace=False, shuffle=False)
            initial_states_used = [self.initial_states[idx] for idx in initial_state_indices]
            # print(initial_states_used)

        generated_adventures: list = list()

        # iterate over initial states used:
        for initial_state in initial_states_used:
            adventure_count = 0
            keep_generating_adventures = True

            while keep_generating_adventures:
                # print("adv count:", adventure_count)

                # generate an adventure with the current initial state:
                goal_generator = ClingoGoalGenerator(adventure_type=self.adv_type, rng_seed=self.rng_seed)
                if not task_config:
                    task_config = {'task': "deliver", 'deliver_to_floor': False}
                # goal_generator.generate_goal_facts(initial_state, task_config, goals_per_adventure)
                goal_generator.generate_goal_facts(initial_state)

                if goal_set_picking == "iterative":
                    goal_set = next(goal_generator.get_goals_iter())

                elif goal_set_picking == "random":
                    # goal_set = goal_generator.get_goals_random(amount=1)
                    goal_set = self.rng.choice(goal_generator.goal_combos, size=1).tolist()[0]

                # print(goal_set)

                cur_adventure = {'initial_state': initial_state, 'goals': goal_set}

                # solve adventure

                # solvable, action_sequence, optimal_turns = self._solve_adventure(cur_adventure, turn_limit=turn_limit)
                solvable, action_sequence, optimal_turns, command_sequence = self._solve_adventure(cur_adventure)

                # print("solvable:", solvable)
                # print("solution:", action_sequence)
                # print("optimal turns:", optimal_turns)

                if not solvable:
                    # print("not solvable, continuing")
                    continue

                # check if optimal turns within bounds

                if min_optimal_turns <= optimal_turns <= max_optimal_turns:

                    # get tuple world state:
                    world_state: set = set()
                    for fact in initial_state:
                        world_state.add(fact_str_to_tuple(fact))

                    # get tuple goals:
                    goal_tuples: list = list()
                    for goal in goal_set:
                        goal_tuples.append(fact_str_to_tuple(goal))

                    if task_config['task'] == 'deliver':
                        goal_strings: list = list()
                        for goal_tuple in goal_tuples:
                            # get string representations of delivery item and target:
                            item_type: str = str()
                            item_adjs: list = list()
                            target_type: str = str()
                            target_adjs: list = list()
                            for fact in world_state:
                                if fact[0] == "type":
                                    if goal_tuple[1] == fact[1]:
                                        item_type = self.entity_definitions[fact[2]]['repr_str']
                                    if goal_tuple[2] == fact[1]:
                                        target_type = self.entity_definitions[fact[2]]['repr_str']
                                if fact[0] == "adj":
                                    if goal_tuple[1] == fact[1]:
                                        item_adjs.append(fact[2])
                                    if goal_tuple[2] == fact[1]:
                                        target_adjs.append(fact[2])
                            item_adjs_str: str = " ".join(item_adjs)
                            if item_adjs:
                                item_str: str = f"{item_adjs_str} {item_type}"
                            else:
                                item_str: str = f"{item_type}"
                            target_adjs_str: str = " ".join(target_adjs)
                            if target_adjs:
                                target_str: str = f"{target_adjs_str} {target_type}"
                            else:
                                target_str: str = f"{target_type}"
                            goal_str: str = f"the {item_str} {goal_tuple[0]} the {target_str}"
                            goal_strings.append(goal_str)
                        # print(goal_strings)

                        if len(goal_strings) == 1:
                            goal_desc: str = f"Put {goal_strings[0]}."
                        if len(goal_strings) == 2:
                            goal_desc: str = f"Put {goal_strings[0]} and {goal_strings[1]}."
                        if len(goal_strings) >= 3:
                            goal_listing_str: str = ", ".join(goal_strings[:-1])
                            goal_desc: str = f"Put {goal_listing_str} and {goal_strings[-1]}."

                        # print(goal_desc)

                    viable_adventure = {
                        'adventure_type': self.adv_type,
                        'goal': goal_desc, 'initial_state': initial_state, 'goal_state': goal_set,
                        'optimal_turns': optimal_turns,
                        'optimal_solution': action_sequence, 'optimal_commands': command_sequence,
                        'action_definitions': self.adv_type_def['action_definitions'],
                        'room_definitions': self.adv_type_def['room_definitions'],
                        'entity_definitions': self.adv_type_def['entity_definitions'],
                        'bench_turn_limit': self.adv_type_def['bench_turn_limit']
                    }

                    # TODO: use one absolute turn limit for everything

                    generated_adventures.append(viable_adventure)
                    adventure_count += 1
                    if adventures_per_initial_state and adventure_count == adventures_per_initial_state:
                        keep_generating_adventures = False
                else:
                    continue
        # print(generated_adventures)

        if save_to_file:
            with open(f"generated_{self.adv_type}_adventures.json", 'w', encoding='utf-8') as out_adv_file:
                if indent_output_json:
                    out_adv_file.write(json.dumps(generated_adventures, indent=2))
                else:
                    out_adv_file.write(json.dumps(generated_adventures))

        return generated_adventures

    def generate_adventures_(self,
                            load_initial_states_from_file: str = "",
                            initial_state_limit: int = 0, initial_state_picking: str = "iterative",
                            adventures_per_initial_state: int = 0,
                            goal_set_picking: str = "iterative",
                            save_to_file: bool = True, indent_output_json: bool = True):
        """
        Generate adventures based on parameters.
        The total number of adventures generated is initial_state_limit * adventures_per_initial_state - if both are 0,
        a very large number of adventures will be generated. All 1-object-per-type, non-adjective basic/house initial
        states already number over 240k, so these values should be limited. Use RNG seeds to reproduce smaller sets of
        adventures that have been picked randomly.
        :param task_config: Task configuration, currently only 'deliver' exists. (Might also determine initial state
            generation in the future.)
        :param load_initial_states_from_file: If a file path is passed, pre-generated initial states are loaded,
            otherwise all possible initial states are generated.
        :param initial_state_limit: The maximum number of initial states to generate adventures for. If 0 (default), ALL
            available initial states will be used.
        :param initial_state_picking: Method to pick from all possible goal states:
            "iterate" - Picks initial states from the first available iteratively until initial_state_limit is reached.
            "random" - Picks random initial states from all available until initial_state_limit is reached.
        :param adventures_per_initial_state: How many adventures to generate for each initial state.
        :param goals_per_adventure: How many goals each adventure has.
        :param goal_set_picking: Method to pick from all possible goal states:
            "iterate" - Picks goal sets from the first permutation iteratively until goals_per_adventure is met.
            "random" - Picks random goal sets from all permutations until goals_per_adventure is met.
        :param turn_limit: Maximum number of turns that optimal solution generator can take.
        :param min_optimal_turns: Adventures that need less than this number of turns to solve will be discarded.
        :param max_optimal_turns: Adventures that need more than this number of turns to solve will be discarded.
        :param save_to_file: File name for saving generated adventures. If empty string, generated adventures will not
            be saved.
        """

        task_config: dict = self.adv_type_def["task_config"]

        goals_per_adventure: int = self.adv_type_def["goal_count"]

        turn_limit: int = self.adv_type_def["optimal_solver_turn_limit"]
        min_optimal_turns: int = self.adv_type_def["min_optimal_turns"]
        max_optimal_turns: int = self.adv_type_def["max_optimal_turns"]

        # INTIAL STATES
        # NOTE: As the number of room layouts is relatively small, generating all to iterate over is viable.
        # generate room layouts:


        # set up initial states:
        if load_initial_states_from_file:
            self._load_initial_states_from_file(load_initial_states_from_file)
        else:
            self._generate_initial_states()

        # get initial states to generate adventures with:
        if initial_state_picking == "iterative":
            if initial_state_limit:
                initial_states_used = [self.initial_states[idx] for idx in range(initial_state_limit)]
            else:
                initial_states_used = self.initial_states
        elif initial_state_picking == "random":
            assert initial_state_limit > 0, ("Random initial state picking without a limit is equivalent to getting all"
                                             " iteratively.")
            # initial_states_used = self.rng.choice(self.initial_states, size=initial_state_limit, replace=False, shuffle=False).tolist()
            # print(type(self.initial_states))
            initial_state_indices = self.rng.choice(len(self.initial_states), size=initial_state_limit, replace=False, shuffle=False)
            initial_states_used = [self.initial_states[idx] for idx in initial_state_indices]
            # print(initial_states_used)

        generated_adventures: list = list()

        # iterate over initial states used:
        for initial_state in initial_states_used:
            adventure_count = 0
            keep_generating_adventures = True

            while keep_generating_adventures:
                # print("adv count:", adventure_count)

                # generate an adventure with the current initial state:
                goal_generator = ClingoGoalGenerator(adventure_type=self.adv_type, rng_seed=self.rng_seed)
                if not task_config:
                    task_config = {'task': "deliver", 'deliver_to_floor': False}
                # goal_generator.generate_goal_facts(initial_state, task_config, goals_per_adventure)
                goal_generator.generate_goal_facts(initial_state)

                if goal_set_picking == "iterative":
                    goal_set = next(goal_generator.get_goals_iter())

                elif goal_set_picking == "random":
                    # goal_set = goal_generator.get_goals_random(amount=1)
                    goal_set = self.rng.choice(goal_generator.goal_combos, size=1).tolist()[0]

                # print(goal_set)

                cur_adventure = {'initial_state': initial_state, 'goals': goal_set}

                # solve adventure

                # solvable, action_sequence, optimal_turns = self._solve_adventure(cur_adventure, turn_limit=turn_limit)
                solvable, action_sequence, optimal_turns, command_sequence = self._solve_adventure(cur_adventure)

                # print("solvable:", solvable)
                # print("solution:", action_sequence)
                # print("optimal turns:", optimal_turns)

                if not solvable:
                    # print("not solvable, continuing")
                    continue

                # check if optimal turns within bounds

                if min_optimal_turns <= optimal_turns <= max_optimal_turns:

                    # get tuple world state:
                    world_state: set = set()
                    for fact in initial_state:
                        world_state.add(fact_str_to_tuple(fact))

                    # get tuple goals:
                    goal_tuples: list = list()
                    for goal in goal_set:
                        goal_tuples.append(fact_str_to_tuple(goal))

                    if task_config['task'] == 'deliver':
                        goal_strings: list = list()
                        for goal_tuple in goal_tuples:
                            # get string representations of delivery item and target:
                            item_type: str = str()
                            item_adjs: list = list()
                            target_type: str = str()
                            target_adjs: list = list()
                            for fact in world_state:
                                if fact[0] == "type":
                                    if goal_tuple[1] == fact[1]:
                                        item_type = self.entity_definitions[fact[2]]['repr_str']
                                    if goal_tuple[2] == fact[1]:
                                        target_type = self.entity_definitions[fact[2]]['repr_str']
                                if fact[0] == "adj":
                                    if goal_tuple[1] == fact[1]:
                                        item_adjs.append(fact[2])
                                    if goal_tuple[2] == fact[1]:
                                        target_adjs.append(fact[2])
                            item_adjs_str: str = " ".join(item_adjs)
                            if item_adjs:
                                item_str: str = f"{item_adjs_str} {item_type}"
                            else:
                                item_str: str = f"{item_type}"
                            target_adjs_str: str = " ".join(target_adjs)
                            if target_adjs:
                                target_str: str = f"{target_adjs_str} {target_type}"
                            else:
                                target_str: str = f"{target_type}"
                            goal_str: str = f"the {item_str} {goal_tuple[0]} the {target_str}"
                            goal_strings.append(goal_str)
                        # print(goal_strings)

                        if len(goal_strings) == 1:
                            goal_desc: str = f"Put {goal_strings[0]}."
                        if len(goal_strings) == 2:
                            goal_desc: str = f"Put {goal_strings[0]} and {goal_strings[1]}."
                        if len(goal_strings) >= 3:
                            goal_listing_str: str = ", ".join(goal_strings[:-1])
                            goal_desc: str = f"Put {goal_listing_str} and {goal_strings[-1]}."

                        # print(goal_desc)

                    viable_adventure = {
                        'adventure_type': self.adv_type,
                        'goal': goal_desc, 'initial_state': initial_state, 'goal_state': goal_set,
                        'optimal_turns': optimal_turns,
                        'optimal_solution': action_sequence, 'optimal_commands': command_sequence,
                        'action_definitions': self.adv_type_def['action_definitions'],
                        'room_definitions': self.adv_type_def['room_definitions'],
                        'entity_definitions': self.adv_type_def['entity_definitions'],
                        'bench_turn_limit': self.adv_type_def['bench_turn_limit']
                    }

                    # TODO: use one absolute turn limit for everything

                    generated_adventures.append(viable_adventure)
                    adventure_count += 1
                    if adventures_per_initial_state and adventure_count == adventures_per_initial_state:
                        keep_generating_adventures = False
                else:
                    continue
        # print(generated_adventures)

        if save_to_file:
            with open(f"generated_{self.adv_type}_adventures.json", 'w', encoding='utf-8') as out_adv_file:
                if indent_output_json:
                    out_adv_file.write(json.dumps(generated_adventures, indent=2))
                else:
                    out_adv_file.write(json.dumps(generated_adventures))

        return generated_adventures


if __name__ == "__main__":
    """
    import time
    test_generator = ClingoAdventureGenerator()

    # test_gen_config = {"entity_adjectives": "optional"}  # "optional" takes a long time to generate due to the amount of variations
    # test_gen_config = {"entity_adjectives": "all"}  # "all" takes a long time to generate due to the amount of variations
    test_gen_config = {"entity_adjectives": "none"}  # "none" takes the shortest time (<1m for basic) to generate due to the low amount of variations

    gen_start_time = time.time()

    test_gen = test_generator.generate_adventures(test_gen_config)
    # test_gen = test_generator.generate_adventures(test_gen_config, save_to_file=True)

    gen_end_time = time.time()

    print(f"Generated {len(test_gen)} adventure initial world states in {gen_end_time - gen_start_time}s.")
    """

    initial_state_gen = ClingoInitialStateGenerator(adventure_type="home_deliver_three")

    generated_layouts_path = "generated_home_layouts.json"
    # initial_state_gen.generate_room_layouts(layout_file_path=generated_layouts_path)

    # generated_initials_path = "generated_home_deliver_initial_states.json"
    generated_initials_path = "test_home_deliver_initial_states.jsonl"
    initial_state_gen.generate_initial_states(layout_file_path=generated_layouts_path,
                                              initial_state_file_path=generated_initials_path)

    """
    with open("generated_adventures.json", 'r', encoding='utf-8') as advs_file:
        adventures = json.load(advs_file)
        adventure = adventures[0]
        print(adventure)
    """

    # test_adv = ['at(kitchen1floor,kitchen1)', 'at(pantry1floor,pantry1)', 'at(hallway1floor,hallway1)', 'at(livingroom1floor,livingroom1)', 'at(broomcloset1floor,broomcloset1)', 'at(table1,livingroom1)', 'at(counter1,kitchen1)', 'at(refrigerator1,pantry1)', 'at(shelf1,kitchen1)', 'at(freezer1,pantry1)', 'at(pottedplant1,hallway1)', 'at(chair1,livingroom1)', 'at(couch1,livingroom1)', 'at(broom1,broomcloset1)', 'at(sandwich1,pantry1)', 'at(apple1,pantry1)', 'at(banana1,pantry1)', 'at(player1,livingroom1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,hallway1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(kitchen1floor,floor)', 'type(pantry1floor,floor)', 'type(hallway1floor,floor)', 'type(livingroom1floor,floor)', 'type(broomcloset1floor,floor)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)', 'type(banana1,banana)', 'support(kitchen1floor)', 'support(pantry1floor)', 'support(hallway1floor)', 'support(livingroom1floor)', 'support(broomcloset1floor)', 'support(table1)', 'support(counter1)', 'support(shelf1)', 'on(broom1,broomcloset1floor)', 'on(pottedplant1,hallway1floor)', 'container(refrigerator1)', 'container(freezer1)', 'in(banana1,refrigerator1)', 'in(apple1,refrigerator1)', 'in(sandwich1,refrigerator1)', 'openable(refrigerator1)', 'openable(freezer1)', 'closed(refrigerator1)', 'closed(freezer1)', 'takeable(pottedplant1)', 'takeable(broom1)', 'takeable(sandwich1)', 'takeable(apple1)', 'takeable(banana1)', 'movable(pottedplant1)', 'movable(broom1)', 'movable(sandwich1)', 'movable(apple1)', 'movable(banana1)', 'needs_support(pottedplant1)', 'needs_support(broom1)', 'needs_support(sandwich1)', 'needs_support(apple1)', 'needs_support(banana1)']
    # test_adv = ['at(kitchen1floor,kitchen1)', 'at(pantry1floor,pantry1)', 'at(hallway1floor,hallway1)', 'at(livingroom1floor,livingroom1)', 'at(broomcloset1floor,broomcloset1)', 'at(table1,livingroom1)', 'at(counter1,kitchen1)', 'at(refrigerator1,pantry1)', 'at(shelf1,kitchen1)', 'at(freezer1,pantry1)', 'at(pottedplant1,hallway1)', 'at(chair1,livingroom1)', 'at(couch1,livingroom1)', 'at(broom1,broomcloset1)', 'at(sandwich1,pantry1)', 'at(apple1,pantry1)', 'at(banana1,pantry1)', 'at(player1,livingroom1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,hallway1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(kitchen1floor,floor)', 'type(pantry1floor,floor)', 'type(hallway1floor,floor)', 'type(livingroom1floor,floor)', 'type(broomcloset1floor,floor)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)', 'type(banana1,banana)', 'support(kitchen1floor)', 'support(pantry1floor)', 'support(hallway1floor)', 'support(livingroom1floor)', 'support(broomcloset1floor)', 'support(table1)', 'support(counter1)', 'support(shelf1)', 'on(broom1,broomcloset1floor)', 'on(pottedplant1,hallway1floor)', 'container(refrigerator1)', 'container(freezer1)', 'in(banana1,refrigerator1)', 'in(apple1,refrigerator1)', 'in(sandwich1,refrigerator1)', 'openable(refrigerator1)', 'openable(freezer1)', 'takeable(pottedplant1)', 'takeable(broom1)', 'takeable(sandwich1)', 'takeable(apple1)', 'takeable(banana1)', 'movable(pottedplant1)', 'movable(broom1)', 'movable(sandwich1)', 'movable(apple1)', 'movable(banana1)', 'needs_support(pottedplant1)', 'needs_support(broom1)', 'needs_support(sandwich1)', 'needs_support(apple1)', 'needs_support(banana1)']
    """
    test_goal_gen = ClingoGoalGenerator()

    test_goal_gen.generate_goal_facts(test_adv)
    # print(test_goal_gen.get_goals_random(amount=2))
    
    test_iter_goals = [next(test_goal_gen.get_goals_iter()) for goal_combo in range(3)]
    print(test_iter_goals)
    test_iter_goals = [next(test_goal_gen.get_goals_iter()) for goal_combo in range(3)]
    print(test_iter_goals)
    
    test_iter_goals = next(test_goal_gen.get_goals_iter())
    print(test_iter_goals)
    test_iter_goals = next(test_goal_gen.get_goals_iter())
    print(test_iter_goals)
    """
    """
    test_solver = ClingoAdventureSolver()
    
    # test_solver.initialize_adventure(test_adv)

    # test_solver.convert_actions()
    solvable, solution = test_solver.solve_optimally(test_adv, ["on(sandwich1,table1)"], turn_limit=50)
    # solvable, solution, encoding = test_solver.solve_optimally(test_adv, ["on(sandwich1,table1)"], turn_limit=50, return_encoding=True)

    # print(encoding)

    print("Adventure is solvable:", solvable)
    # print(solution)

    commands, turns = test_solver.convert_adventure_solution(solution)
    print(f"The adventure is optimally solved in {turns} turns with the following action sequence:")
    print(commands)
    """
    """
    solution = "action_t(0,go,hallway1) action_t(3,open,refrigerator1) action_t(4,take,sandwich1) action_t(1,go,kitchen1) action_t(6,go,hallway1) action_t(2,go,pantry1) action_t(5,go,kitchen1) action_t(7,go,livingroom1) action_t(8,put,sandwich1,table1)"

    convert_adventure_solution(solution)

    """
    """
    for initial_adv in test_gen:
        adv_solver = ClingoAdventureSolver()
    """
    """
    test_generator = ClingoAdventureGenerator()
    
    test_generator.generate_adventures(task_config={}, load_initial_states_from_file="generated_initial_states.json",
                                       initial_state_limit=1, initial_state_picking="random",
                                       adventures_per_initial_state=2, goal_set_picking="random", goals_per_adventure=3,
                                       max_optimal_turns=30)
    """
    """
    test_generator.generate_adventures(load_initial_states_from_file="generated_home_deliver_initial_states.json",
                                       initial_state_limit=1, initial_state_picking="random",
                                       adventures_per_initial_state=2, goal_set_picking="random")
    """

    # test_base = ClingoAdventureBase()
