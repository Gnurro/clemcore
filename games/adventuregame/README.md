# adventuregame
Interactive Fiction/Text Adventure clemgame
## Metrics
Standard clembench metrics are implemented, metrics listed here are adventuregame-specific metrics.
### Turn-level
Goal score: How many goal states have been achieved at this turn. Records **change** of the number of achieved goal 
states, meaning that if less goal states are achieved at this turn, the number is negative.
### Episode-level
turns_over_par: Number of turns taken over the optimal number of turns. If adventure is finished as fast as possible, 
this score is 0. Recorded as `NaN` if adventure was not successfully finished.  
turn_ratio: Ratio of turns taken within the possible range of turns. Possible range of turns `turn_range` is the number 
of turns between the optimal number of turns and the turn limit. Calculated as `1 - turns_over_par / turn_range`, so 
that this score is 1.0 if the number of turns taken is the optimal number of turns. Recorded as `NaN` if adventure was 
not successfully finished.  
achieved_goal_ratio: Ratio of achieved goal states by total adventure goal states. 1.0 if all goal states are achieved, 
0.0 if none are achieved. Recorded regardless of successful finish and aborting.  
full_rating / BENCH_SCORE: Combines achieved goals and turns taken into overall score. Calculated as 
`achieved_goal_ratio * turn_ratio`, so that achievement of all goals in the optimal number of turns results in a score 
of 1.0. Taking more turns than optimal to achieve all goals lowers the score, as does not achieving all goals before the 
adventure ends. The latter is relevant in case reaching the maximum number of turns leads to a 'loss' end, but the 
episode was not aborted due to invalid format or similar - scores in these cases will be very low (due to 
lowest-possible turn_ratio), but not 0.0.  
### Note
For the current clembench framework, aborted episodes are to receive a `NaN` BENCH_SCORE - but in adventuregame, a 
model can achieve a number of goal states *before* an episode is aborted. How to record and evaluate this type of 
'partial success despite abort' is an open question.