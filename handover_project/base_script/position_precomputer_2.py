import pandas as pd

df_name_1 = "200km_sc9_padova.csv"
df_name_2 = "200km_sc9_munich.csv"
df_name_3 = "200km_sc9_lucerna.csv"

df_names = [df_name_1, df_name_2, df_name_3]

for df_name in df_names:
    df = pd.read_csv(df_name)

    df['occurrence_countdown'] = df.groupby('sat_name').cumcount(ascending=False) + 1

    filename = f"{df_name.split('.')[0]}_countdown.csv"
    df.to_csv(filename, index=False)