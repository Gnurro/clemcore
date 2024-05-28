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

        # generation config:
        self.generation_config = dict()
        # TODO: set up generation config usage; load from json

    def generate_adventures(self):

        clingo_str = str()

        # TODO: use generation config once implemented
        if not self.generation_config:
            # add player type fact:
            player_fact = "type(player1,player)."
            self.clingo_control.add(player_fact)
            clingo_str += "\n" + player_fact
            # generate with one room each:
            for room_type_name, room_type_values in self.room_definitions.items():
                # basic atoms:
                room_id = f"{room_type_name}1"  # default to 'kitchen1' etc
                # print("room:", room_id)
                type_atom = f"room({room_id},{room_type_name})."
                # add type atom to clingo controller:
                self.clingo_control.add(type_atom)
                clingo_str += "\n" + type_atom
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
                break
            # print("solve get:", solve.get())

        print(raw_adventures)
        """"""
        # ADVENTURE FORMAT CONVERSION
        result_adventures = list()
        for raw_adventure in raw_adventures:
            fact_list = raw_adventure.split()
            # remove 'reachable' helper atoms:
            fact_list = [fact for fact in fact_list if "reachable" not in fact]
            result_adventures.append(fact_list)

        print(result_adventures)


if __name__ == "__main__":
    test_generator = ClingoAdventureGenerator()
    test_gen = test_generator.generate_adventures()
