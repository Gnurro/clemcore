# AdventureGame
AdventureGame is a Interactive Fiction/Text Adventure clemgame.  
The model is given descriptions of rooms and their contents, along with a task, and interacts with the game world by 
giving action commands. The IF interpreter changes the game world state based on the given action or returns a textual 
failure response if that is not possible.
## Instantiation
### Adventure Generation
The Clingo Answer Set solver is used to generate viable initial world state sets based on room and entity definitions. 
These initial world states are used to create goal sets via script. Initial world states and task goal sets are combined 
into adventures. As a last step, Clingo is used to generate the optimal solution for each adventure, using action 
definitions.  
Each step above can output intermediate adventures for manual editing, which was used to create the v1 set of adventures 
with two difficulty levels. Difficulty is based on the accessibility of task objects and the complexity of tasks, which 
are easy to manipulate at an intermediate stage that has generated initial world states and goal sets, but no optimal 
solution yet. An example JSON file of that stage is `adventuregame/resources/adv_source.json`.
### Instances
Different prompts are used for the two game variants, 'basic' and 'planning', to generate two instance sets from the 
same pool of adventures. This means that the initial world state and goal sets are identical between the 'basic' and 
'planning' variants for each difficulty - 'basic-easy' instance 0 has the same adventure as 'planning-easy' instance 0.
## Evaluation
### Metrics
Standard clembench metrics are implemented, metrics listed here are AdventureGame-specific metrics.
#### Turn-level
goal_score: How many goal states have been achieved at this turn. Records **change** of the number of achieved goal 
states, meaning that if less goal states are achieved at this turn, the number is negative.
#### Episode-level
turns_over_par: Number of turns taken over the optimal number of turns. If adventure is finished as fast as possible, 
this score is 0. Recorded as `NaN` if adventure was not successfully finished.  
turn_ratio: Ratio of turns taken within the possible range of turns. Possible range of turns `turn_range` is the number 
of turns between the optimal number of turns and the turn limit. Calculated as `1 - turns_over_par / turn_range`, so 
that this score is 1.0 if the number of turns taken is the optimal number of turns. Recorded as `NaN` if adventure was 
not successfully finished.  
achieved_goal_ratio: Ratio of achieved goal states by total adventure goal states. 1.0 if all goal states are achieved, 
0.0 if none are achieved. Recorded regardless of successful finish and aborting.  
BENCH_SCORE: `achieved_goal_ratio * 100` to fit expected scale of clemgame quality scores as used in the overall 
clemscore.  
