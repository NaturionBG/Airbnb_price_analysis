import gradio as gr
import pandas as pd
from catboost import CatBoostRegressor
import numpy as np
import os

model = CatBoostRegressor()
if 'GUI' in os.getcwd():
  model.load_model('airbnb_catboost.cmb')
else:
  model.load_model('./GUI/airbnb_catboost.cmb')

features = ['bedrooms', 'beds', 'baths', 'luxury_items', 'luxury_score', 'location_desirability', 'quality', 'city']

def fetch_sole_prediction(*args) -> int | float:
  global model
  global features
  try:
    X = pd.DataFrame([args], columns = features)
    result = round(model.predict(X)[0], 2)
    return f'''[>] CODEBREAKER  SYSTEM: Given listing's predicted cost: {result}RUB.'''
  except Exception as e:
    return f'''[>] CODEBREAKER  SYSTEM: An Error has occured.'''
  
  
def fetch_batch_prediction(file) -> pd.DataFrame:
  global model
  global features
  try:
    X = pd.read_csv(file.name,)
    result = model.predict(X)
    df = pd.DataFrame({
      'Sequential ID': np.linspace(1, len(result), len(result)),
      'Predicted Price, RUB': result 
    })
    df.set_index('Sequential ID', drop=True)
    return df
  except Exception:
    return f'''[>] CODEBREAKER  SYSTEM: An Error has occured.'''

regular_message = '''
<h1>[>] CODEBREAKER  SYSTEM:</h1>
<em>
Please input numerical or categorical values into the boxes below.  
Adhere strictly to the instructions.  

If you wish to process a batch, submit a CSV file into the corresponding field in the BATCH tab.
</em>

<strong>
If any errors arise, you shall be informed\n.
</strong>
'''

greet_message = '''
<h1>[>] CODEBREAKER  SYSTEM:</h1>

<strong>
Greetings, user!

- Codebreaker service status: operational.

You may proceed.
</strong>
'''

with gr.Blocks(title = 'CODEBREAKER') as Log:
  gr.Markdown(greet_message)
  gr.Markdown(regular_message)
  
  with gr.Tab("Singular"):
    with gr.Row():
      with gr.Column():
        bedrooms = gr.Number(label='Enter the numeric amount of Bedrooms.', minimum=0)
        beds = gr.Number(label='Enter the numeric amount of Beds.', minimum=0)
        baths = gr.Number(label='Enter the numeric amount of Baths.', minimum=0)
        luxury_items = gr.Number(label='Enter the numeric amount of any items outside of regular Beds, Baths and Bedrooms.', minimum=0)
        luxury_score = gr.Slider(0, 100, label='Choose the luxury score for your listing. 0 - 100', step=1)
        location_desirability = gr.Slider(0, 100, label='Choose the location desirability score for your listing. 0 - 100', step=1)
        city = gr.Dropdown(['Boston', 'Los Angeles', 'New York', 'Houston', 'Nashville', 'Seattle', 'Denver', 'San Francisco', 'Somerville', 'Cambridge', 'Topanga'], label='Choose the city where this listing is situated.')
        quality = gr.Dropdown(['acceptable', 'great', 'perfect'], label='Choose what condition the quarters in the listing are in.')
        predictor = gr.Button('Submit for Evaluation.')
    with gr.Column():
      output = gr.Textbox(label = 'Your Result.')
  
    predictor.click(
      fn = fetch_sole_prediction,
      inputs = [bedrooms, beds, baths, luxury_items, luxury_score, location_desirability, quality, city],
      outputs = output
    )
  
  with gr.Tab('Batch'):
    csv_input = gr.File(label='Or submit a CSV file for batch processing.', file_types=['.csv'])
    batch_predictor = gr.Button('Submit for Processing')
    output_df = gr.Dataframe(label = 'Batch Results')
    batch_predictor.click(fn=fetch_batch_prediction, inputs=csv_input, outputs=output_df)


Log.launch(theme=gr.themes.Cyberpunk())
