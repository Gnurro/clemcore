"""
Clingo-based adventure generation and optimal solving.
"""

from typing import List, Dict, Tuple, Any, Union, Optional
import json
from clingo.control import Control

from adv_util import fact_str_to_tuple, fact_tuple_to_str


# TODO: define/doc adventure generation config format and contents


class ClingoAdventureBase(object):
    """
    Wraps the clingo ASP module. Base class for adventure generator and adventure solver.
    """
    def __init__(self):
        # initialize clingo controller:
        self.clingo_control: Control = Control(["0"])  # ["0"] argument to return all models

        # load room type definitions:
        with open("basic_rooms.json", 'r', encoding='utf-8') as rooms_file:
            room_definitions = json.load(rooms_file)

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
        with open("basic_entities.json", 'r', encoding='utf-8') as entities_file:
            entity_definitions = json.load(entities_file)

        # print(entity_definitions)
        self.entity_definitions = dict()
        for type_def in entity_definitions:
            type_def_dict = dict()
            for type_key, type_value in type_def.items():
                if not type_key == 'type_name':
                    type_def_dict[type_key] = type_value
            self.entity_definitions[type_def['type_name']] = type_def_dict

        # print(self.entity_definitions)


class ClingoAdventureGenerator(ClingoAdventureBase):
    """
    Generates initial adventure state sets based on room and entity definitions.
    """
    def __init__(self):
        super().__init__()

    def generate_adventures(self, generation_config: dict = {}):

        clingo_str = str()

        # TODO: use generation config once implemented
        # if not self.generation_config:

        # add player type fact:
        player_fact = "type(player1,player)."
        self.clingo_control.add(player_fact)
        clingo_str += "\n" + player_fact
        # add rule for random player start location:
        player_location_rule = "1 { at(player1,ROOM):room(ROOM,_) } 1."
        self.clingo_control.add(player_location_rule)
        clingo_str += "\n" + player_location_rule

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

                if not generation_config["entity_adjectives"] == "none":
                    if "possible_adjs" in entity_type_values:
                        # adjective rule:
                        possible_adj_list = list()
                        for possible_adj in entity_type_values["possible_adjs"]:
                            possible_adj_str = f"adj({entity_id},{possible_adj})"
                            possible_adj_list.append(possible_adj_str)
                        possible_adjs = ";".join(possible_adj_list)
                        if generation_config["entity_adjectives"] == "optional":
                            adj_rule = "0 { $POSSIBLEADJS$ } 1."
                        elif generation_config["entity_adjectives"] == "all":
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
        # solve combined LP for raw adventures:
        raw_adventures = list()

        with self.clingo_control.solve(yield_=True) as solve:
            for model in solve:
                # print("model:", model)
                raw_adventures.append(model.__str__())
                # break
            # print("solve get:", solve.get())

        # print(raw_adventures)
        """"""
        # ADVENTURE FORMAT CONVERSION
        result_adventures = list()
        for raw_adventure in raw_adventures:
            fact_list = raw_adventure.split()
            # remove 'reachable' helper atoms:
            fact_list = [fact for fact in fact_list if "reachable" not in fact]
            result_adventures.append(fact_list)

        print(result_adventures)
        """
        for result_adventure in result_adventures:
            for fact in result_adventure:
                # if "in(" in fact:
                #    print(fact)
                if "on(" in fact:
                    print(fact)
        """
        return result_adventures


class ClingoAdventureSolver(ClingoAdventureBase):
    """
    Solves adventure with given goal states, optimizing action sequence.
    """
    def __init__(self):
        super().__init__()
        # load action definitions:
        with open("basic_actions.json", 'r', encoding='utf-8') as actions_file:
            action_definitions = json.load(actions_file)

        # print(room_definitions)
        self.action_definitions = dict()
        for type_def in action_definitions:
            type_def_dict = dict()
            for type_key, type_value in type_def.items():
                if not type_key == 'type_name':
                    type_def_dict[type_key] = type_value
            self.action_definitions[type_def['type_name']] = type_def_dict

        # print(self.action_definitions)

        # load action definitions:
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

    def initialize_adventure(self, initial_world_state, mutable_fact_types: List = ["at", "in", "on", "closed", "open"],
                             return_encoding: bool = False):
        """
        Set up initial world state and add facts to clingo controller.
        Turn facts have _t in the fact/atom type, and their first value is the turn at which they are true.
        """
        if return_encoding:
            clingo_str = str()

        # convert fact strings to tuples:
        initial_facts = [fact_str_to_tuple(fact) for fact in initial_world_state]
        # iterate over initial world state, add fixed basic facts, add turn facts for changeable facts
        for fact in initial_facts:
            # print(fact)
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

        if return_encoding:
            return clingo_str

    def solve_optimally(self, initial_world_state, goal_facts: list, turn_limit: int = 10,
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
            initial_state_clingo = self.initialize_adventure(initial_world_state, return_encoding=True)
            clingo_str += "\n" + initial_state_clingo
        else:
            self.initialize_adventure(initial_world_state)

        # add actions:
        for action_name, action_def in self.action_definitions.items():
            action_asp = action_def['asp']
            self.clingo_control.add(action_asp)
            if return_encoding:
                clingo_str += "\n" + action_asp

        # add goals:
        for goal in goal_facts:
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
            satisfiable = solve.get()
            if satisfiable == "SAT":
                solvable = True
            elif satisfiable == "UNSAT":
                solvable = False

        if return_only_optimal:
            if return_encoding:
                return solvable, raw_solutions[-1], clingo_str
            return solvable, raw_solutions[-1], clingo_str

        if return_encoding:
            return solvable, raw_solutions, clingo_str
        return solvable, raw_solutions


if __name__ == "__main__":
    """
    test_generator = ClingoAdventureGenerator()

    # test_gen_config = {"entity_adjectives": "optional"}  # "optional" takes a long time to generate due to the amount of variations
    # test_gen_config = {"entity_adjectives": "all"}  # "all" takes a long time to generate due to the amount of variations
    test_gen_config = {"entity_adjectives": "none"}  # "none" takes the shortest time (<1m for basic) to generate due to the low amount of variations

    test_gen = test_generator.generate_adventures(test_gen_config)
    """

    test_solver = ClingoAdventureSolver()

    test_adv = ['at(kitchen1floor,kitchen1)', 'at(pantry1floor,pantry1)', 'at(hallway1floor,hallway1)', 'at(livingroom1floor,livingroom1)', 'at(broomcloset1floor,broomcloset1)', 'at(table1,livingroom1)', 'at(counter1,kitchen1)', 'at(refrigerator1,pantry1)', 'at(shelf1,kitchen1)', 'at(freezer1,pantry1)', 'at(pottedplant1,hallway1)', 'at(chair1,livingroom1)', 'at(couch1,livingroom1)', 'at(broom1,broomcloset1)', 'at(sandwich1,pantry1)', 'at(apple1,pantry1)', 'at(banana1,pantry1)', 'at(player1,livingroom1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,hallway1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(kitchen1floor,floor)', 'type(pantry1floor,floor)', 'type(hallway1floor,floor)', 'type(livingroom1floor,floor)', 'type(broomcloset1floor,floor)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)', 'type(banana1,banana)', 'support(kitchen1floor)', 'support(pantry1floor)', 'support(hallway1floor)', 'support(livingroom1floor)', 'support(broomcloset1floor)', 'support(table1)', 'support(counter1)', 'support(shelf1)', 'on(broom1,broomcloset1floor)', 'on(pottedplant1,hallway1floor)', 'container(refrigerator1)', 'container(freezer1)', 'in(banana1,refrigerator1)', 'in(apple1,refrigerator1)', 'in(sandwich1,refrigerator1)', 'openable(refrigerator1)', 'openable(freezer1)', 'takeable(pottedplant1)', 'takeable(broom1)', 'takeable(sandwich1)', 'takeable(apple1)', 'takeable(banana1)', 'movable(pottedplant1)', 'movable(broom1)', 'movable(sandwich1)', 'movable(apple1)', 'movable(banana1)', 'needs_support(pottedplant1)', 'needs_support(broom1)', 'needs_support(sandwich1)', 'needs_support(apple1)', 'needs_support(banana1)']
    # test_solver.initialize_adventure(test_adv)

    # test_solver.convert_actions()
    test_solver.solve_optimally(test_adv, ["open(refrigerator1)"])
