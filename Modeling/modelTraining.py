import os
import pandas as pd
from sklearn.model_selection import train_test_split
import sys
import json
from sklearn.metrics import confusion_matrix, f1_score, make_scorer, fbeta_score
from sklearn.model_selection import GridSearchCV, cross_val_score
from lightgbm import LGBMClassifier
from sklearn.preprocessing import binarize
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report
import joblib
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE
import optuna

# Retrieve parameters from command-line arguments
params = json.loads(sys.argv[1])
st_date = params["st_date"]
end_date = params["end_date"]
data_universe = params["data_universe"]

if data_universe == 'fha':
    bucket = ["FHA", "VA"]
elif data_universe == 'conventional':
    bucket = ["CONVENTIONAL", "PMI"]

# st_date =  "2023-05"
# end_date = "2024-05"
# test_date = "2024-06"
# data_universe = 'fha'
# if data_universe == 'fha':
#     bucket = ["FHA", "VA"]
# elif data_universe == 'conventional':
#     bucket = ["CONVENTIONAL", "PMI"]

# Define paths and load data
files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_directory = os.path.join(files_path, "modeling_data")
training_path = os.path.join(root_directory, 'training_data_'+str(end_date)+'.csv')
BSI_training_data = pd.read_csv(training_path)

# Drop unnecessary columns and handle missing values
data = BSI_training_data.copy()


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


X = data.drop(["Refinanced_3_months_lookahead"], axis=1)
y = data["Refinanced_3_months_lookahead"].astype(int)

print(y.value_counts())

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, stratify=y, test_size=0.2, random_state=0
)

imputer = SimpleImputer(strategy='mean')
X_train_imputed = imputer.fit_transform(X_train)

# Resample training data to balance classes using SMOTE
smote = SMOTE(random_state=42, sampling_strategy=0.1) #auto") #0.5)  #1)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train_imputed, y_train)


# # Step 1: Hyperparameter Tuning with GridSearchCV
# param_grid = {
#     'n_estimators': [200], #[100, 200, 300],
#     'max_depth': [5], #[5, 7, 10],
#     'learning_rate': [0.01], #[0.01, 0.05, 0.1],
#     'subsample': [0.5], #[0.6, 0.8, 1.0],
#     'colsample_bytree': [0.5], #[0.6, 0.8, 1.0],
#     'class_weight': ['balanced'],
#     'reg_alpha': [0.1]#, 'is_unbalance']  # Balances weights automatically
# }

# # Step 1: Hyperparameter Tuning with GridSearchCV
# param_grid = {
#     'n_estimators': [100, 200, 300],
#     'max_depth': [5, 7, 10],
#     'learning_rate': [0.01, 0.05, 0.1],
#     'subsample': [0.2,0.6, 0.8],
#     'colsample_bytree': [0.5], #[0.2,0.6, 0.8],
#     'class_weight': ['balanced'],
#     'reg_alpha': [0.1]#, 'is_unbalance']  # Balances weights automatically
# }

# Custom scoring: Penalize false positives by emphasizing precision or other custom metrics
def custom_metric(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    accuracy = accuracy_score(y_test, y_pred)
    TN, FP, FN, TP = cm.ravel()
    f1 = f1_score(y_true, y_pred, zero_division=0)
    # # Penalize false positives more heavily
    # score = TP - 2*(FP)  # Example: Heavily penalize FP
    score = fbeta_score(y_test, y_pred, beta=2, zero_division=0)

    return score


# Custom weighted binary cross-entropy loss for LightGBM
def custom_loss(y_true, y_pred):
    import numpy as np
    # Transform predictions with sigmoid
    p = 1 / (1 + np.exp(-y_pred))

    # Define class weights
    w_1 = 2  # Weight for class 1 (minority)
    w_0 = 1  # Weight for class 0 (majority)

    # Compute gradient and hessian
    grad = -(w_1 * y_true - w_0 * (1 - y_true)) * (p - y_true)
    hess = p * (1 - p) * (w_1 * y_true + w_0 * (1 - y_true))

    return grad, hess


custom_scorer = make_scorer(custom_metric, greater_is_better=True)

#
# Define the objective function for Optuna
def objective(trial):
    # Define the search space for hyperparameters
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 180, 220),  # Around 200
        'max_depth': trial.suggest_int('max_depth', 4, 6),  # Around 5
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.02),  # Around 0.01
        'subsample': trial.suggest_float('subsample', 0.4, 0.6),  # Around 0.5
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 0.6),  # Around 0.5
        'class_weight': 'balanced',  # Fixed
        'reg_alpha': 0.1  # Fixed
    }

    # Initialize the model with trial parameters
    model = LGBMClassifier(**params, verbose=-1)

    # Train the model
    model.fit(X_train_resampled, y_train_resampled)

    # Predict on validation data (use the same split logic as in GridSearchCV)
    # y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob > 0.5).astype(int)  # Default threshold = 0.5

    # Calculate custom metric
    return custom_metric(y_test, y_pred)


# Create an Optuna study
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)

# Retrieve the best parameters and model
best_params = study.best_params
print(f"Best parameters: {best_params}")

# Train the best model on the entire resampled dataset
best_model = LGBMClassifier(**best_params, verbose=-1)
best_model.fit(X_train_resampled, y_train_resampled)

# # Initialize GridSearchCV with LightGBM model
# grid_search = GridSearchCV(
#     estimator=LGBMClassifier(verbose=-1),
#     param_grid=param_grid,
#     scoring=custom_scorer,  # Focus on reducing false positives
#     # cv=10,  # 5-fold cross-validation
#     n_jobs=-1
# )
#
# # Perform grid search
# grid_search.fit(X_train_resampled, y_train_resampled)
#
# # Best model after hyperparameter tuning
# best_model = grid_search.best_estimator_
# print(f"Best parameters: {grid_search.best_params_}")
#
# # Train the model using the best parameters and evaluate
# best_model.fit(X_train_resampled, y_train_resampled)

# Evaluate the optimized model with default threshold (0.5)
y_prob = best_model.predict_proba(X_test)[:, 1]
y_pred = (y_prob > 0.5).astype(int)  # Default threshold = 0.5

# Print evaluation metrics
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Evaluate thresholds for performance (focus on reducing false positives)
def evaluate_thresholds(model, X_test, y_test):
    thresholds = [i / 10 for i in range(1, 10)]
    best_threshold = None
    best_fbeta = -1  # Initialize with a value lower than any possible F-beta score
    beta = 2  # Adjust beta as needed to focus more on recall

    for threshold in thresholds:
        # Get predicted probabilities for the positive class
        y_prob = model.predict_proba(X_test)[:, 1]

        # Apply the threshold to get predictions
        y_pred = binarize(y_prob.reshape(-1, 1), threshold=threshold)

        # Compute confusion matrix and other metrics
        cm = confusion_matrix(y_test, y_pred)
        TN, FP, FN, TP = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        fbeta = fbeta_score(y_test, y_pred, beta=beta, zero_division=0)

        # Update best threshold if the current F-beta is higher
        if fbeta > best_fbeta:
            best_fbeta = fbeta
            best_threshold = threshold

        print(f"Threshold: {threshold}")
        print(f"Confusion Matrix:\n{cm}")
        print(f"Accuracy: {accuracy}")
        print(f"Precision: {precision}")
        print(f"Recall: {recall}")
        print(f"Specificity: {specificity}")
        print(f"F1 Score: {f1}")
        print(f"F{beta} Score: {fbeta}")
        print("-" * 50)

    print(f"Best Threshold: {best_threshold}")
    print(f"Best F{beta} Score: {best_fbeta}")
    return best_threshold


# Evaluate the model at various thresholds
best_threshold = evaluate_thresholds(best_model, X_test, y_test)

# Cross-validation on the best model
lightgbm_cv_scores = cross_val_score(
    best_model, X_train_resampled, y_train_resampled, cv=10, scoring='f1'
)
print(f"Cross-validation scores: {lightgbm_cv_scores}")
print(f"Mean CV score: {lightgbm_cv_scores.mean()}")

save_data = {
        "model": best_model,
        "best_threshold": best_threshold,
    }

# # Save the trained model to disk
files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
best_model_path = os.path.join(files_path, "Modeling", "BestModel", f"best_model_{end_date}_{data_universe}.pkl")
joblib.dump(save_data, best_model_path)
print(f"Model saved to {best_model_path}")
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# import os
# import pandas as pd
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import confusion_matrix, classification_report
# from sklearn.ensemble import IsolationForest
# from imblearn.over_sampling import SMOTE
# from sklearn.preprocessing import StandardScaler
# from lightgbm import LGBMClassifier
# from sklearn.metrics import make_scorer
#
# # Define paths and load data
# root_directory = "/Users/abhilashchenreddy/PycharmProjects/BSI/modeling_data"
# training_path = os.path.join(root_directory, "training_data.csv")
# BSI_training_data = pd.read_csv(training_path)
#
# # Drop unnecessary columns and handle missing values
# data = BSI_training_data.copy()
# data.drop(["LoanNumber"], axis=1, inplace=True)
# data.fillna({
#     "FICO_Score": data["FICO_Score"].mean(),
#     "Login_Count": data["Login_Count"].mean(),
#     "Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher":
#         data["Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher"].mean(),
#     "Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars":
#         data["Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars"].mean(),
#     "Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied":
#         data["Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied"].mean(),
# }, inplace=True)
# data = data[data.LoanType.isin(['FHA', 'VA'])]
#
# categorical_columns = data.select_dtypes(include=['object']).columns
# data = pd.get_dummies(data, columns=categorical_columns, drop_first=True)
#
# # Define features and target
# X = data.drop(["Refinanced_3_months_lookahead"], axis=1)
# y = data["Refinanced_3_months_lookahead"].astype(int)
#
# # Split data into training and testing sets
# X_train, X_test, y_train, y_test = train_test_split(
#     X, y, stratify=y, test_size=0.2, random_state=0
# )
#
# # Impute missing values
# from sklearn.impute import SimpleImputer
# imputer = SimpleImputer(strategy='mean')
# X_train_imputed = imputer.fit_transform(X_train)
#
# # Resample training data to balance classes using SMOTE
# smote = SMOTE(random_state=42, sampling_strategy='auto')
# X_train_resampled, y_train_resampled = smote.fit_resample(X_train_imputed, y_train)
#
# # Scale data for Isolation Forest
# scaler = StandardScaler()
# X_train_scaled = scaler.fit_transform(X_train_resampled)
# X_test_scaled = scaler.transform(X_test)
#
# # Isolation Forest for anomaly detection (One-Class Classification)
# iso_forest = IsolationForest(contamination=0.01, random_state=42)
# iso_forest.fit(X_train_scaled[y_train_resampled == 0])  # Train only on the majority class (non-defaults)
#
# # Isolation Forest Predictions
# iso_forest_predictions = iso_forest.predict(X_test_scaled)
# iso_forest_predictions = np.where(iso_forest_predictions == -1, 1, 0)  # Map -1 to 1 (outliers), 1 to 0 (inliers)
#
# # LightGBM hyperparameter tuning
# param_grid = {
#     'n_estimators': [200],
#     'max_depth': [5],
#     'learning_rate': [0.01],
#     'subsample': [0.5],
#     'colsample_bytree': [0.5],
#     'class_weight': ['balanced'],
#     'reg_alpha': [0.1]
# }
#
# # Custom scoring function
# def custom_metric(y_true, y_pred):
#     cm = confusion_matrix(y_true, y_pred)
#     TN, FP, FN, TP = cm.ravel()
#     return f1_score(y_true, y_pred, zero_division=0)
#
# custom_scorer = make_scorer(custom_metric, greater_is_better=True)
#
# # GridSearchCV for LightGBM
# grid_search = GridSearchCV(
#     estimator=LGBMClassifier(verbose=-1),
#     param_grid=param_grid,
#     scoring=custom_scorer,
#     cv=5,
#     n_jobs=-1
# )
# grid_search.fit(X_train_resampled, y_train_resampled)
# best_model = grid_search.best_estimator_
#
# # Train the best model
# best_model.fit(X_train_resampled, y_train_resampled)
#
# # Evaluate LightGBM
# lgbm_probabilities = best_model.predict_proba(X_test)[:, 1]
# lgbm_predictions = (lgbm_probabilities > 0.5).astype(int)
#
# # Combine Isolation Forest and LightGBM
# combined_predictions = np.logical_and(lgbm_predictions, iso_forest_predictions).astype(int)
#
# # Evaluation
# print("Confusion Matrix (Combined):")
# print(confusion_matrix(y_test, combined_predictions))
# print("Classification Report (Combined):")
# print(classification_report(y_test, combined_predictions))

# Save best model
# best_model_path = "/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel/best_model.pkl"
# joblib.dump(best_model, best_model_path)
# print(f"Model saved to {best_model_path}")
