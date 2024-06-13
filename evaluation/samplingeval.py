"""
Compile results of multiple benchmark passes with sampling.
"""

import os
import pandas as pd

# NOTE: This script expects that bencheval.py has already been run on the individual pass_N directories.

# PASSES_PATH = f"..{os.sep}clembench-runs{os.sep}v1.6_sampling{os.sep}"
# PASSES_PATH = f"results{os.sep}v1.6_sampling{os.sep}"
PASSES_PATH = f"../results/v1.6_sampling/"

PASSES = [0, 1, 2, 3, 4]

# load results CSV of each pass:

pass_results: list = list()

for bench_pass in PASSES:
    with open(f"{PASSES_PATH}pass_{bench_pass}/results.csv", 'r', encoding='utf-8') as pass_csv_file:
        pass_results.append(pd.read_csv(pass_csv_file))

# print(pass_results)

combined = pd.concat(pass_results)

# print(combined)
# print(combined.describe())

# combined.to_csv("combined_passes.csv")

# print(combined.iloc[:, 0])

model_temps = pd.unique(combined.iloc[:, 0])
# print(model_temps)

# print(combined.loc[model_temps[0], 0])

# print(combined.iloc[:, 0] == model_temps[0])


means_dict = dict()

for model_temp in model_temps:
    model_temp_rows = combined[combined.iloc[:, 0] == model_temp]

    # print(model_temp_rows)
    # print(model_temp_rows.describe())

    model_temp_means = model_temp_rows.iloc[:, 1:].mean()

    # print(model_temp_means)

    means_dict[f"{model_temp}"] = model_temp_means


# means_df = pd.DataFrame(model_temp_means)
means_df = pd.DataFrame(means_dict)

# print(means_df)

# pivoted = means_df.pivot(columns=0)
pivoted = means_df.T

print(pivoted)


pivoted.to_csv("means.csv")