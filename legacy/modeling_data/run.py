import subprocess
import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys

# Initialize default parameters
default_params = {
    "st_date": "2024-06",   #"2022-08"
    "end_date": "2025-06",    #"2023-08"
    "data_universe": "fha",
    "test_date": "2025-07"
}

# Check for command-line arguments (JSON string)
if len(sys.argv) > 1:
    try:
        # Parse the JSON parameters
        input_params = json.loads(sys.argv[1])
        # Update the default parameters with provided values
        default_params.update(input_params)
        print(f"Using parameters from command line: {default_params}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON parameters: {e}")
        print("Using default parameters")

# Set the parameters from the combined dict
st_date = default_params["st_date"]
end_date = default_params["end_date"]
data_universe = default_params["data_universe"]
test_date = default_params["test_date"]

# Get the dynamic base path using the current script location
files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print("files_path:", files_path)

# Serialize parameters as JSON to pass them as a single string
params = json.dumps({
    "st_date": st_date,
    "end_date": end_date,
    "test_date": test_date,
    "data_universe": data_universe,
})

# Input variables
training_data_folder = os.path.join(files_path, "modeling_data")
output_file = f"training_data_{end_date}.csv"
file_path = os.path.join(training_data_folder, output_file)
best_model_path = os.path.join(files_path, "Modeling", "BestModel", f"best_model_{end_date}_{data_universe}.pkl")

# Calculate next month for prediction data
date_obj = datetime.strptime(test_date, "%Y-%m")
pred_date = (date_obj + relativedelta(months=1)).strftime("%Y-%m")

# Script paths
training_script_path = os.path.join(files_path, "data_preperation", "TrainingDataPreperation_new_features.py")
model_training_fha_script_path = os.path.join(files_path, "Modeling", "modelTraining.py")
model_training_conventional_script_path = os.path.join(files_path, "Modeling", "modelTraining_conventional.py")
prediction_data_script_path = os.path.join(files_path, "Modeling", "PredictionDataPreperation.py")
inference_script_path = os.path.join(files_path, "Modeling", "ModelInference.py")

# File paths
test_pred_data_path = os.path.join(training_data_folder, f"prediction_data_{end_date}.csv")
test_data_path = os.path.join(files_path, "inference_data", f"PayoffReason{pred_date}.xlsx")

# Get the full path to the Python interpreter in the virtual environment
python_executable = sys.executable

def run_script(script_path, script_params):
    """
    Utility function to run a script with given parameters and handle errors.
    """
    try:
        # Run the script with the virtual environment's Python and pass parameters
        result = subprocess.run(
            [python_executable, script_path, script_params],  # Pass script_params as an argument
            check=True,
            text=True
        )

        print(f"Script executed successfully: {script_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the script: {script_path}")
        print(f"Error: {e}")
        sys.exit(1)

# Check for training data
if not os.path.exists(file_path):
    print(f"Training data file does not exist: {file_path}")
    run_script(training_script_path, params)
else:
    print(f"Training data file exists: {file_path}")

# Check for trained model
if not os.path.exists(best_model_path):
    print(f"Trained model file does not exist: {best_model_path}")
    if data_universe == 'fha':
        run_script(model_training_fha_script_path, params)
    elif data_universe == 'conventional':
        run_script(model_training_conventional_script_path, params)

else:
    print(f"Trained model file exists: {best_model_path}")

# Check for prediction data
if not os.path.exists(test_pred_data_path):
    print(f"Prediction data file does not exist: {test_pred_data_path}")
    run_script(prediction_data_script_path, params)
else:
    print(f"Prediction data file exists: {test_pred_data_path}")

# Check for inference data
if not os.path.exists(test_data_path):
    raise FileNotFoundError(f"Inference data file does not exist: {test_data_path}")

# If both prediction and inference data files exist, run inference
print(f"Both prediction and inference data files are present.")
run_script(inference_script_path, params)
