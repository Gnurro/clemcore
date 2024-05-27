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
                type_atom = f"room({room_id},{room_type_name})."
                # add type atom to clingo controller:
                self.clingo_control.add(type_atom)
                clingo_str += "\n" + type_atom
                # add exit rule:
                for exit_target in room_type_values['exit_targets']:
                    if 'max_connections' in room_type_values:
                        exit_rule = "1 { exit(ROOM,TARGET) } $EXITLIMIT$ :- room(ROOM,$ROOMTYPE$), room(TARGET,$TARGETTYPE$), TARGET != ROOM."
                        # -> there can be 1 or 2 exits from this room type to the exit_target room type
                        exit_rule = exit_rule.replace("$EXITLIMIT$", str(room_type_values['max_connections']))
                        exit_rule = exit_rule.replace("$ROOMTYPE$", room_type_name)
                        exit_rule = exit_rule.replace("$TARGETTYPE$", exit_target)
                        # print(exit_rule)
                        # add exit rule to clingo controller:
                        self.clingo_control.add(exit_rule)
                        clingo_str += "\n" + exit_rule
                    else:
                        # print(exit_target)
                        exit_rule = "1 { exit(ROOM,TARGET) } 2 :- room(ROOM,$ROOMTYPE$), room(TARGET,$TARGETTYPE$), TARGET != ROOM."
                        # -> there can be 1 or 2 exits from this room type to the exit_target room type
                        exit_rule = exit_rule.replace("$ROOMTYPE$", room_type_name)
                        exit_rule = exit_rule.replace("$TARGETTYPE$", exit_target)
                        # print(exit_rule)
                        # add exit rule to clingo controller:
                        self.clingo_control.add(exit_rule)
                        clingo_str += "\n" + exit_rule


                    # TODO: add single-access rooms
                    # TODO: add 'passage' helper atoms
                    """
                    if 'max_connections' in room_type_values:
                        max_connection_rule = ":- $EXITLIMIT$ { exit($ROOMID$,OTHERROOM): room(OTHERROOM,_) }."
                        max_connection_rule = max_connection_rule.replace("$EXITLIMIT$", str(room_type_values['max_connections']+2))
                        max_connection_rule = max_connection_rule.replace("$ROOMID$", room_id)
                        print(max_connection_rule)
                        self.clingo_control.add(max_connection_rule)
                        clingo_str += "\n" + max_connection_rule
                        """

        print(clingo_str)

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
            result_adventures.append(fact_list)

        print(result_adventures)


if __name__ == "__main__":
    test_generator = ClingoAdventureGenerator()
    test_gen = test_generator.generate_adventures()
