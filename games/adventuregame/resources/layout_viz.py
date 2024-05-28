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

# raw_facts = 'room(kitchen1,kitchen) room(pantry1,pantry) room(hallway1,hallway) exit(kitchen1,pantry1) exit(kitchen1,hallway1) exit(pantry1,kitchen1) exit(hallway1,kitchen1)'

# raw_facts = "room(kitchen1,kitchen) room(pantry1,pantry) room(hallway1,hallway) exit(kitchen1,hallway1) exit(pantry1,hallway1) exit(hallway1,kitchen1) exit(hallway1,pantry1)"
# raw_facts = "room(kitchen1,kitchen) room(pantry1,pantry) room(hallway1,hallway) room(livingroom1,livingroom) room(broomcloset1,broomcloset) exit(kitchen1,pantry1) exit(kitchen1,livingroom1) exit(pantry1,kitchen1) exit(hallway1,broomcloset1) exit(livingroom1,kitchen1) exit(broomcloset1,hallway1) reachable(pantry1,kitchen1) reachable(livingroom1,kitchen1) reachable(kitchen1,pantry1) reachable(broomcloset1,hallway1) reachable(kitchen1,livingroom1) reachable(hallway1,broomcloset1)"
raw_facts = "room(kitchen1,kitchen) room(pantry1,pantry) room(hallway1,hallway) room(livingroom1,livingroom) room(broomcloset1,broomcloset) exit(kitchen1,pantry1) exit(kitchen1,livingroom1) exit(kitchen1,hallway1) exit(pantry1,kitchen1) exit(hallway1,kitchen1) exit(hallway1,broomcloset1) exit(livingroom1,kitchen1) exit(broomcloset1,hallway1) reachable(kitchen1,pantry1) reachable(kitchen1,livingroom1) reachable(kitchen1,hallway1) reachable(pantry1,kitchen1) reachable(pantry1,hallway1) reachable(hallway1,kitchen1) reachable(hallway1,pantry1) reachable(hallway1,livingroom1) reachable(hallway1,broomcloset1) reachable(livingroom1,kitchen1) reachable(livingroom1,hallway1) reachable(broomcloset1,hallway1) reachable(kitchen1,broomcloset1) reachable(pantry1,broomcloset1) reachable(livingroom1,broomcloset1) reachable(pantry1,livingroom1) reachable(broomcloset1,livingroom1) reachable(livingroom1,pantry1) reachable(broomcloset1,pantry1) reachable(broomcloset1,kitchen1)"

# adventure_facts = raw_facts.split()

# adventure_facts = ['at(apple1,kitchen1)', 'at(sandwich1,pantry1)', 'at(broom1,broomcloset1)', 'at(couch1,livingroom1)', 'at(chair1,livingroom1)', 'at(pottedplant1,hallway1)', 'at(freezer1,pantry1)', 'at(shelf1,kitchen1)', 'at(refrigerator1,kitchen1)', 'at(counter1,kitchen1)', 'at(table1,livingroom1)', 'at(player1,hallway1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,livingroom1)', 'exit(kitchen1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,kitchen1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)']
# adventure_facts = ['at(player1,broomcloset1)', 'at(table1,livingroom1)', 'at(counter1,kitchen1)', 'at(refrigerator1,pantry1)', 'at(shelf1,pantry1)', 'at(freezer1,pantry1)', 'at(pottedplant1,livingroom1)', 'at(chair1,livingroom1)', 'at(couch1,livingroom1)', 'at(broom1,broomcloset1)', 'at(sandwich1,pantry1)', 'at(apple1,pantry1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,hallway1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)', 'support(table1)', 'support(counter1)', 'support(shelf1)', 'container(refrigerator1)', 'container(freezer1)', 'in(refrigerator1,refrigerator1)']
adventure_facts = ['at(table1,livingroom1)', 'at(counter1,kitchen1)', 'at(refrigerator1,pantry1)', 'at(shelf1,pantry1)', 'at(freezer1,pantry1)', 'at(pottedplant1,livingroom1)', 'at(chair1,livingroom1)', 'at(couch1,livingroom1)', 'at(broom1,broomcloset1)', 'at(sandwich1,pantry1)', 'at(apple1,pantry1)', 'at(player1,livingroom1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,hallway1)', 'exit(pantry1,hallway1)', 'exit(hallway1,kitchen1)', 'exit(hallway1,pantry1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,hallway1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)', 'type(table1,table)', 'type(counter1,counter)', 'type(refrigerator1,refrigerator)', 'type(shelf1,shelf)', 'type(freezer1,freezer)', 'type(pottedplant1,pottedplant)', 'type(chair1,chair)', 'type(couch1,couch)', 'type(broom1,broom)', 'type(sandwich1,sandwich)', 'type(apple1,apple)', 'support(table1)', 'support(counter1)', 'support(shelf1)', 'container(refrigerator1)', 'container(freezer1)']

# adventure_facts = ['exit(broomcloset1,hallway1)', 'exit(livingroom1,hallway1)', 'exit(livingroom1,kitchen1)', 'exit(hallway1,broomcloset1)', 'exit(hallway1,livingroom1)', 'exit(hallway1,pantry1)', 'exit(hallway1,kitchen1)', 'exit(pantry1,hallway1)', 'exit(pantry1,kitchen1)', 'exit(kitchen1,hallway1)', 'exit(kitchen1,livingroom1)', 'exit(kitchen1,pantry1)', 'room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'type(player1,player)']

# adventure_facts = ['room(kitchen1,kitchen)', 'room(pantry1,pantry)', 'room(hallway1,hallway)', 'room(livingroom1,livingroom)', 'room(broomcloset1,broomcloset)', 'exit(kitchen1,pantry1)', 'exit(kitchen1,livingroom1)', 'exit(pantry1,kitchen1)', 'exit(hallway1,broomcloset1)', 'exit(livingroom1,kitchen1)', 'exit(broomcloset1,hallway1)', 'type(player1,player)']

dot = graphviz.Digraph('room_layout', format='png')

for fact in adventure_facts:
    fact = split_state_string(fact)
    if fact[0] == "room" or fact[0] == "type":
        dot.node(fact[1], fact[1])
    if fact[0] == "exit":
        dot.edge(fact[1], fact[2])
    if fact[0] == "at":
        dot.edge(fact[1], fact[2], "at")
    if fact[0] == "on":
        dot.edge(fact[1], fact[2], "on")
    if fact[0] == "in":
        dot.edge(fact[1], fact[2], "in")

dot.render()
