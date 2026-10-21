# Databricks Model Inference Application

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip

### Installation
1. Install required packages:
   ```
   pip install -r requirements.txt
   ```

### Databricks Connection Configuration
To connect to Databricks DBFS, you need to set the following environment variables:

```bash
export DATABRICKS_HOST="https://your-databricks-instance.cloud.databricks.com"
export DATABRICKS_TOKEN="your-personal-access-token"
```

Alternatively, for Windows:
```cmd
set DATABRICKS_HOST=https://your-databricks-instance.cloud.databricks.com
set DATABRICKS_TOKEN=your-personal-access-token
```

### Running the Application
```
python app.py
```
# Refinance Propensity Model

This project contains the code for predicting the propensity of mortgage loans to refinance based on various factors including loan characteristics, credit information, demographic data, and user behavior.

## Overview

The model uses an ensemble approach combining Linear Regression and Random Forest models to predict which loans are likely to refinance in the near future. It analyzes key factors such as interest rate differences, loan-to-value ratios, FICO scores, and user login activity to identify refinance candidates.

## Project Structure

- `BSI_Refinance_Prediction.ipynb`: Jupyter notebook with the complete workflow for data preparation, model training, and prediction
- `data_preperation/`: Directory containing data preprocessing scripts
- `Modeling/`: Directory containing model training and inference scripts
- `modeling_data/`: Directory where training and prediction data are stored
- `inference_data/`: Directory for input data files

## Prerequisites

- Python 3.8+
- Jupyter Notebook
- Required packages: pandas, numpy, scikit-learn, matplotlib, seaborn

## Running the Model

### Using the Jupyter Notebook

1. Open `BSI_Refinance_Prediction.ipynb` in Jupyter Notebook or JupyterLab
2. Configure the parameters in the configuration cell at the beginning
3. Run all cells to execute the complete workflow

### Using the Python Scripts

Alternatively, you can run the model using the following command:

```bash
python modeling_data/run.py '{"st_date": "2024-05", "end_date": "2025-05", "test_date": "2025-06", "data_universe": "conventional"}'  
```

Where:
- `st_date`: Start date for training data (YYYY-MM)
- `end_date`: End date for training data (YYYY-MM)
- `test_date`: Date for test/prediction data (YYYY-MM)
- `data_universe`: Either "conventional" or "fha"

## Web Application

A web application for running the model is also available. To launch it:

```bash
python app.py
```

Then navigate to http://localhost:8000 in your web browser.

## Input Data

The model requires the following input data files in the `inference_data` directory:

- `one_off_oct23_to_Feb25.csv`: Main loan data file
- `Interest Rate Data.xlsx`: Interest rate matrix
- `BSI_CREDITREPORTING.xlsx`: Credit report data
- `MLW_logins.csv`: User login activity data
- `PayoffReason{YYYY-MM}.xlsx`: Payoff reason data for the prediction month

Additional reference data required in `data_preperation/Input`:

- `Zip_FIPS_Mapping.csv`: ZIP code to FIPS code mapping
- `Census_Demographic.csv`: Demographic data by FIPS code
- `HPI.xlsx`: House Price Index data

## Output

The model generates the following outputs in the `modeling_data` directory:

- `training_data_{end_date}.csv`: Prepared training data
- `prediction_data_{end_date}.csv`: Prepared prediction data
- `final_predictions{pred_date}_{data_universe}.csv`: Final predictions with refinance probabilities
- Various charts and visualizations

## Model Details

The model uses an ensemble approach with two component models:

1. **Linear Regression Ensemble**: Multiple linear regression models trained on random subsets of data
2. **Random Forest Ensemble**: Multiple random forest models with varying feature selections

These models are combined using a threshold-based approach to generate the final refinance predictions.
The application will be available at http://localhost:8000

### Troubleshooting
- If you encounter "No module named 'pyspark.dbutils'" error, ensure you're using the Databricks SDK approach as implemented in the application.
- If files aren't being copied from DBFS, verify your Databricks connection parameters and permissions.
- For large files, the application implements chunked downloading to handle the 1MB per request limit of the DBFS API.
- If you encounter permission issues, ensure your Databricks access token has the proper permissions to read from the specified DBFS path.

### Notes on File Download Methods
The application uses multiple methods to download files from DBFS:

1. **Small Files**: Uses `dbutils.fs.head()` to retrieve the file content directly

2. **Large Files**: If the simple head method fails due to size limitations, the application attempts to use the Databricks Files API (`ws.files.download()`) for direct file download

3. **Fallback**: For environments where direct download isn't available, you may need to use the Databricks CLI to download large files:
   ```
   databricks fs cp dbfs:/FileStore/path/to/file local/path
   ```

If you encounter persistent issues with large file downloads, consider setting up a Databricks job to preprocess the files into smaller chunks before attempting to download them.
