import graphviz


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



adventure_facts = ['exit(broomcloset1,hallway1)', 'exit(livingroom1,hallway1)', 'exit(livingroom1,kitchen1)', 'exit(hallway1,broomcloset1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,pantry1)', 'exit(hallway1,kitchen1)', 'exit(pantry1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(kitchen1,hallway1)', 'exit(kitchen1,livingroom1)', 'exit(kitchen1,pantry1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'type(player1,player)']

dot = graphviz.Digraph('room_layout')

for fact in adventure_facts:
    fact = split_state_string(fact)
    if fact[0] == "room":
        dot.node(fact[1], fact[1])
    if fact[0] == "exit":
        dot.edge(fact[1], fact[2])

dot.render()
