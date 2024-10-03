import pandas as pd
from config import INPUT_CSV_PATH, OUTPUT_CSV_PATH

def apply_transformations(df):
    # Applying transformation: cv

    # Select only the targeted columns
    targeted_columns = []
    df = df[targeted_columns]
    return df

if __name__ == '__main__':
    df = pd.read_csv(INPUT_CSV_PATH)
    transformed_df = apply_transformations(df)
    transformed_df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f'Transformed CSV saved to {OUTPUT_CSV_PATH}')
