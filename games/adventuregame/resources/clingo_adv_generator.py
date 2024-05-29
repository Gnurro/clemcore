import json
from clingo.control import Control


class AdventureGenerationConfig(dict):
    """
    Holds configuration for adventure generation.
    """


class ClingoAdventureGenerator:
    """
    Wraps the clingo ASP solver module.
    Generates initial adventure state sets based on room and entity definitions.
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

        print(self.entity_definitions)

        # generation config:
        self.generation_config = dict()
        # TODO: set up generation config usage; load from json

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


if __name__ == "__main__":
    test_generator = ClingoAdventureGenerator()

    # test_gen_config = {"entity_adjectives": "optional"}  # "optional" takes a long time to generate due to the amount of variations
    # test_gen_config = {"entity_adjectives": "all"}  # "all" takes a long time to generate due to the amount of variations
    test_gen_config = {"entity_adjectives": "none"}  # "none" takes the shortest time (<1m for basic) to generate due to the low amount of variations

    test_gen = test_generator.generate_adventures(test_gen_config)
