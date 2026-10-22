import pandas as pd
import joblib
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.preprocessing import binarize
import os
import sys
import json
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_preperation.BuildFeatures_new_features import normalize_loan_number  # F19 fix

# Retrieve parameters from command-line arguments
#params = json.loads(sys.argv[1])

params = json.loads(sys.argv[1])
print(params)
st_date = params["st_date"]
end_date = params["end_date"]
data_universe = params["data_universe"]
test_date =params["test_date"]

if data_universe == 'fha':
    bucket = ["FHA", "VA"]
elif data_universe == 'conventional':
    bucket = ["CONVENTIONAL", "PMI"]

# st_date = "2024-10"
# end_date = "2024-10"
# data_universe = "conventional"
# test_date ="2024-11"

# if data_universe == 'fha':
#     bucket = ["FHA", "VA"]
# elif data_universe == 'conventional':
#     bucket = ["CONVENTIONAL", "PMI"]

# st_date = "2023-05"
# end_date = "2024-05"
# test_date = "2024-06"
# data_universe = 'fha'
# if data_universe == 'fha':
#     bucket = ["FHA", "VA"]
# elif data_universe == 'conventional':
#     bucket = ["CONVENTIONAL", "PMI"]

# Parse the string into a datetime object
date_obj = datetime.strptime(test_date, "%Y-%m")
next_month = date_obj + relativedelta(months=1)
pred_date = next_month.strftime("%Y-%m")

# Path to the saved model
files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
best_model_path = os.path.join(files_path, "Modeling", "BestModel", f"best_model_{end_date}_{data_universe}.pkl")
print(best_model_path)
saved_data = joblib.load(best_model_path)
lightgbm_model = saved_data["model"]
best_threshold = saved_data["best_threshold"]
# F31 fix, corrected: lightgbm_model.feature_name_ is generic "Column_N" placeholders (the model
# was fit on a bare numpy array), not real column names -- reindexing against it silently zeroes
# every real feature. Use the real training column order saved alongside the model instead.
training_feature_columns = saved_data["feature_columns"]
print("Model loaded successfully!")

# F19 fix: dtype=str on read -- otherwise a CSV round-trip re-infers a purely-numeric-looking
# string column back to int64, silently undoing the string-typing fix made at data-prep time.
test_pred_data = pd.read_csv(
    os.path.join(files_path, "modeling_data", f"prediction_data_{end_date}.csv"),
    dtype={"LoanNumber": str},
)
test_data = pd.read_excel(os.path.join(files_path, "inference_data", f"PayoffReason{pred_date}.xlsx"))
test_data['Refi_flag'] = test_data['Refi'].map({'Yes': 1, 'No': 0})
test_data['Loan Number'] = normalize_loan_number(test_data['Loan Number'])  # F19 fix
test_data = test_data[['Loan Number', 'Refi_flag']]
print("Test prediction data and labels loaded successfully!")


data = test_pred_data.copy()
data.drop(["LoanNumber"], axis=1, inplace=True)
data.fillna({
    "FICO_Score": data["FICO_Score"].mean(),
    "Login_Count": data["Login_Count"].mean(),
    "Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher":
        data["Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher"].mean(),
    "Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars":
        data[
            "Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars"].mean(),
    "Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied":
        data["Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied"].mean(),
}, inplace=True)

data = data[data.LoanType.isin(bucket)]

categorical_columns = data.select_dtypes(include=['object']).columns
print("Categorical Columns:", categorical_columns)
data = pd.get_dummies(data, columns=categorical_columns, drop_first=True)

# Backtest adapter (F31, real-data run): pd.get_dummies() is fit independently on this scoring
# batch, so a category present in training but absent from this specific June batch (e.g. a rare
# credit-rating code) silently produces fewer columns than the model expects, crashing predict().
# Reindex to the REAL training column order saved alongside the model (NOT
# lightgbm_model.feature_name_, which is generic "Column_N" placeholders -- confirmed by an actual
# run: using it silently zeroed every real feature and collapsed pred_prob to one constant value
# for every loan). A missing one-hot category is correctly 0 for every row in this batch; this is
# plumbing to match the matrix shape, not a behavior change.
data = data.reindex(columns=training_feature_columns, fill_value=0)

predictions = lightgbm_model.predict_proba(data)[:, 1]
test_pred_data = test_pred_data[test_pred_data.LoanType.isin(bucket)]
test_pred_data['pred_prob'] = predictions

# Perform a left join on the 'ID' column
test_pred_data = pd.merge(test_pred_data, test_data, how='left', left_on='LoanNumber', right_on='Loan Number', validate='one_to_one')
# F7 fix: the merge above keeps both join-key columns ('LoanNumber' and the actuals file's
# 'Loan Number'); the right-hand one is ~99% null by construction (null wherever this loan has
# no matching refi record, i.e. almost every loan) -- this IS F7's "duplicate, ~100% blank Loan
# Number column", now root-caused: not a raw-data artifact, just left-join residue. Drop it.
test_pred_data.drop(columns=['Loan Number'], inplace=True)
# Fill missing values with 0
test_pred_data['Refi_flag'] = test_pred_data['Refi_flag'] .fillna(0)

print(test_pred_data['Refi_flag'].value_counts())

def evaluate_thresholds(data):
    def metrics(y_true, y_pred, threshold=None):
        # Compute confusion matrix and metrics
        cm = confusion_matrix(y_true, y_pred)
        TN, FP, FN, TP = cm.ravel()
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)  # TN / (TN + FP) if (TN + FP) != 0 else 0
        f1 = f1_score(y_true, y_pred, zero_division=0)

        return recall, specificity

    y_true = data['Refi_flag']
    y_prob = data['pred_prob']

    # Define custom parameter ranges (grid)
    param_ranges = {
        'Interest_Delta_Current_Market': np.linspace(data['Interest_Delta_Current_Market'].min(), data['Interest_Delta_Current_Market'].max(), 5),
        'Ltv_Delta_Orginal_Current': np.linspace(data['Ltv_Delta_Orginal_Current'].min(), data['Ltv_Delta_Orginal_Current'].max(), 5),
        'FICO_Difference': np.linspace(data['FICO_Difference'].min(), data['FICO_Difference'].max(), 5),
    }

    # Define the range of thresholds to test
    thresholds = [i / 10 for i in range(1, 10)]  # Thresholds from 0.1 to 0.9

    # Create a grid of parameter combinations
    for interest_delta in param_ranges['Interest_Delta_Current_Market']:
        for ltv_delta in param_ranges['Ltv_Delta_Orginal_Current']:
            for fico_diff in param_ranges['FICO_Difference']:
                for threshold in thresholds:  # Loop through each threshold

                    data['y_pred'] = (y_prob >= threshold).astype(int)  # Start with dynamic threshold
                    data['y_pred'] = np.where((data['Interest_Delta_Current_Market'] < interest_delta) & (data['y_pred'] == 1), 0, data['y_pred'])
                    data['y_pred'] = np.where((data['Ltv_Delta_Orginal_Current'] > ltv_delta) & (data['y_pred'] == 0), 1, data['y_pred'])
                    data['y_pred'] = np.where((data['FICO_Difference'] > fico_diff) & (data['y_pred'] == 0), 1, data['y_pred'])

                    # Compute metrics and print recall and specificity for the given threshold and parameter combination
                    recall, specificity = metrics(y_true, data['y_pred'], threshold=threshold)
                    if (recall >= 0.7) and (specificity <= 0.3):
                    # if (specificity <= 0.25):
                        print(
                            f"Evaluating with Interest_Delta={interest_delta}, Ltv_Delta={ltv_delta}, FICO_Diff={fico_diff}, Threshold={threshold} -> Recall: {recall:.4f}, Specificity: {specificity:.4f}\n")

def evaluate_thresholds_final(data,fixed_threshold, fixed_interest_delta,fixed_ltv_delta, fixed_fico_diff,  custom=False):
    def metrics(y_true, y_pred):
        # Compute confusion matrix and metrics
        cm = confusion_matrix(y_true, y_pred)
        TN, FP, FN, TP = cm.ravel()
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        return recall, specificity

    y_true = data['Refi_flag']
    y_prob = data['pred_prob']


    # Apply custom logic if specified
    if custom:
        data['y_pred'] = (y_prob >= fixed_threshold).astype(int)  # Start with dynamic threshold
        data['y_pred'] = np.where((data['Interest_Delta_Current_Market'] < fixed_interest_delta) & (data['y_pred'] == 1), 0, data['y_pred'])
        data['y_pred'] = np.where((data['Ltv_Delta_Orginal_Current'] > fixed_ltv_delta) & (data['y_pred'] == 0), 1, data['y_pred'])
        data['y_pred'] = np.where((data['FICO_Difference'] > fixed_fico_diff) & (data['y_pred'] == 0), 1, data['y_pred'])
    else:
        data['y_pred'] = (y_prob >= fixed_threshold).astype(int)

    # Compute metrics
    recall, specificity = metrics(y_true, data['y_pred'])

    # Print results
    print(
        f"Evaluating with Fixed Threshold={fixed_threshold}, "
        f"Interest_Delta={fixed_interest_delta}, "
        f"Ltv_Delta={fixed_ltv_delta}, "
        f"FICO_Diff={fixed_fico_diff} -> Recall: {recall:.4f}, Specificity: {specificity:.4f}\n"
    )

def evaluate_thresholds_with_plot(data, fixed_interest_delta=-1, fixed_ltv_delta=25, fixed_fico_diff=500):
    def metrics(y_true, y_pred):
        cm = confusion_matrix(y_true, y_pred)
        TN, FP, FN, TP = cm.ravel()
        recall = recall_score(y_true, y_pred, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)
        
        # Custom balanced metric with specificity threshold penalty
        # If specificity > 0.3, severely penalize the score
        # Otherwise, prioritize high recall with acceptable specificity
        if specificity > 0.3:
            balanced_score = 0  # Completely disqualify solutions with specificity > 30%
        else:
            balanced_score = recall**2 * (1 - (specificity/0.3))  # Normalize specificity to the 0.3 threshold
            
        return recall, specificity, balanced_score

    y_true = data['Refi_flag']
    y_prob = data['pred_prob']
    
    thresholds = np.arange(0, 0.31, 0.025)
    recalls = []
    specificities = []
    balanced_scores = []
    
    for threshold in thresholds:
        data['y_pred'] = (y_prob >= threshold).astype(int)
        data['y_pred'] = np.where((data['Interest_Delta_Current_Market'] < fixed_interest_delta) & (data['y_pred'] == 1), 0, data['y_pred'])
        data['y_pred'] = np.where((data['Ltv_Delta_Orginal_Current'] > fixed_ltv_delta) & (data['y_pred'] == 0), 1, data['y_pred'])
        data['y_pred'] = np.where((data['FICO_Difference'] > fixed_fico_diff) & (data['y_pred'] == 0), 1, data['y_pred'])
        
        recall, specificity, balanced_score = metrics(y_true, data['y_pred'])
        recalls.append(recall)
        specificities.append(specificity)
        balanced_scores.append(balanced_score)
        print(f"Threshold: {threshold:.3f}, Recall: {recall:.4f}, Specificity: {specificity:.4f}, Balanced Score: {balanced_score:.4f}")

    # Find optimal threshold
    optimal_idx = np.argmax(balanced_scores)
    optimal_threshold = thresholds[optimal_idx]
    print(f"\nOptimal threshold: {optimal_threshold:.3f}")
    print(f"At optimal threshold:")
    print(f"Recall: {recalls[optimal_idx]:.4f}")
    print(f"Specificity: {specificities[optimal_idx]:.4f}")
    print(f"Balanced Score: {balanced_scores[optimal_idx]:.4f}")
    
    # Create the plot with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
    
    # First subplot: Recall and Specificity
    ax1.plot(thresholds, recalls, 'b-', label='Recall')
    ax1.plot(thresholds, specificities, 'r-', label='Specificity')
    ax1.axhline(y=0.3, color='r', linestyle='--', label='Specificity Threshold (30%)')
    ax1.set_xlabel('Threshold')
    ax1.set_ylabel('Score')
    ax1.set_title('Recall and Specificity vs Threshold')
    ax1.legend()
    ax1.grid(True)
    
    # Second subplot: Balanced Score
    ax2.plot(thresholds, balanced_scores, 'g-', label='Balanced Score')
    ax2.axvline(x=optimal_threshold, color='r', linestyle='--', label=f'Optimal Threshold ({optimal_threshold:.3f})')
    ax2.set_xlabel('Threshold')
    ax2.set_ylabel('Balanced Score')
    ax2.set_title('Balanced Score vs Threshold')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plot_path = os.path.join(files_path, 'modeling_data', f'threshold_metrics_plot_{pred_date}_{data_universe}.png')
    plt.savefig(plot_path)
    plt.close()

    # Return optimal metrics
    return {
        'optimal_recall': float(recalls[optimal_idx]),
        'optimal_specificity': float(specificities[optimal_idx])
    }

# Example of running the function with your data
# evaluate_thresholds(test_pred_data)
optimal_metrics = evaluate_thresholds_with_plot(test_pred_data)

# Apply hardcoded threshold to generate final predictions
# Set your hardcoded threshold and parameters here
THRESHOLD = 0.025
INTEREST_DELTA = -1
LTV_DELTA = 25
FICO_DIFF = 500

# Generate predictions using hardcoded threshold
test_pred_data['y_pred'] = (test_pred_data['pred_prob'] >= THRESHOLD).astype(int)
test_pred_data['y_pred'] = np.where((test_pred_data['Interest_Delta_Current_Market'] < INTEREST_DELTA) & (test_pred_data['y_pred'] == 1), 0, test_pred_data['y_pred'])
test_pred_data['y_pred'] = np.where((test_pred_data['Ltv_Delta_Orginal_Current'] > LTV_DELTA) & (test_pred_data['y_pred'] == 0), 1, test_pred_data['y_pred'])
test_pred_data['y_pred'] = np.where((test_pred_data['FICO_Difference'] > FICO_DIFF) & (test_pred_data['y_pred'] == 0), 1, test_pred_data['y_pred'])

# Calculate and print final metrics with hardcoded threshold
y_true = test_pred_data['Refi_flag']
y_pred = test_pred_data['y_pred']
recall = recall_score(y_true, y_pred, zero_division=0)
cm = confusion_matrix(y_true, y_pred)
TN, FP, FN, TP = cm.ravel()
specificity = (TP + FP) / (TN + TP + FP + FN)
print(f"\nFinal metrics with hardcoded threshold {THRESHOLD}:")
print(f"Recall: {recall:.4f}, Specificity: {specificity:.4f}")

# Define the path for the new folder and the output file
output_folder = os.path.join(files_path, 'modeling_data')  # Use absolute path based on files_path
output_file = 'final_predictions'+str(pred_date)+'_'+str(data_universe)+'.csv'   # Replace with your desired file name

# Create the folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Save the dataset (assuming `merged_data` is the DataFrame you want to save)
test_pred_data.to_csv(os.path.join(output_folder, output_file), index=False)

# Print structured results for UI consumption
# Use the same metrics that are printed above for the hardcoded threshold
model_results = {
    'recall': f"{recall:.4f}",
    'specificity': f"{specificity:.4f}"
}

print("MODEL_RESULTS:", json.dumps(model_results))

