import pandera.pandas as pr
import pandas as pd
import numpy as np

blueprint = pr.DataFrameSchema(
  {
    "url": pr.Column(str),
    "description": pr.Column(str),
    "image": pr.Column(str),
    "city": pr.Column(str),
    "guests": pr.Column(np.float64),
    "bedrooms": pr.Column(np.float64),
    "beds": pr.Column(np.float64),
    "baths": pr.Column(np.float64),
    "luxury_items": pr.Column(np.float64),
    "Price": pr.Column(np.float64),
    "s3_url": pr.Column(str),
  }
)

df = pd.read_excel('./dataset/dataset.xlsx')
df[['Price', 'guests', 'bedrooms', 'beds', 'baths', 'luxury_items']] = df[['Price', 'guests', 'bedrooms', 'beds', 'baths', 'luxury_items']].astype(np.float64)
try:
  blueprint.validate(df)
except Exception:
  print('The dataset had failed validation!')
df.loc[:, ['Price', 'description', 'city', 'guests', 'bedrooms', 'beds', 'baths', 'luxury_items', 's3_url']].to_parquet('./dataset/dataset.parquet')
print(df.info())
