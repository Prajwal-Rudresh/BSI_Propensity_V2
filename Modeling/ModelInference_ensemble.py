import os
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression

test_pred_data = pd.read_csv("/Users/abhilashchenreddy/PycharmProjects/BSI/modeling_data/prediction_data.csv")
test_data = pd.read_excel("/Users/abhilashchenreddy/PycharmProjects/BSI/inference_data/PayoffReason2024-07.xlsx")


scaler = joblib.load("/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel/scaler.pkl")
imputer = joblib.load("/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel/imputer.pkl")


test_data['Refi_flag'] = test_data['Refi'].map({'Yes': 1, 'No': 0})
test_data = test_data[['Loan Number', 'Refi_flag']]
print("Test prediction data and labels loaded successfully!")
test_pred_data = test_pred_data[test_pred_data.LoanType.isin(['FHA','VA'])]
test_pred_data = pd.merge(test_pred_data, test_data, how='left', left_on='LoanNumber', right_on='Loan Number')
test_pred_data['Refi_flag'] = test_pred_data['Refi_flag'] .fillna(0)


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
data = data[data.LoanType.isin(['FHA','VA'])]
categorical_columns = data.select_dtypes(include=['object']).columns
print("Categorical Columns:", categorical_columns)
data = pd.get_dummies(data, columns=categorical_columns, drop_first=True)


# Separate features and target
X_test = data.copy()

X_test_imputed = imputer.fit_transform(X_test)
X_test_normalized = scaler.fit_transform(X_test_imputed)

class LinearRegressionEnsemble:
    def __init__(self, n_models, row_fraction, col_fraction):
        self.n_models = n_models
        self.row_fraction = row_fraction
        self.col_fraction = col_fraction
        self.models = []
        self.selected_features = []

    def fit(self, X, y):
        for i in range(self.n_models):
            # Randomly select a fraction of rows and columns
            row_indices = np.random.choice(X.shape[0], int(self.row_fraction * X.shape[0]), replace=False)
            col_indices = np.random.choice(X.shape[1], int(self.col_fraction * X.shape[1]), replace=False)

            X_sub = X[row_indices][:, col_indices]
            y_sub = y[row_indices]

            # Train a linear regression model
            model = LinearRegression()
            model.fit(X_sub, y_sub)

            # Store the model and selected features
            self.models.append(model)
            self.selected_features.append(col_indices)

    def predict(self, X):
        predictions = np.zeros((self.n_models, X.shape[0]))

        # Each model makes predictions based on its selected features
        for i, model in enumerate(self.models):
            X_sub = X[:, self.selected_features[i]]
            predictions[i] = model.predict(X_sub)

        # Average predictions across models
        average_predictions = np.mean(predictions, axis=0)
        return average_predictions


# Ensemble of Random Forest Models
class RandomForestEnsemble:
    def __init__(self, n_models, row_fraction, col_fraction, n_estimators=50):
        self.n_models = n_models
        self.row_fraction = row_fraction
        self.col_fraction = col_fraction
        self.n_estimators = n_estimators
        self.models = []
        self.selected_features = []

    def fit(self, X, y):
        for i in range(self.n_models):
            # Randomly select a fraction of rows and columns
            row_indices = np.random.choice(X.shape[0], int(self.row_fraction * X.shape[0]), replace=False)
            col_indices = np.random.choice(X.shape[1], int(self.col_fraction * X.shape[1]), replace=False)

            X_sub = X[row_indices][:, col_indices]
            y_sub = y[row_indices]

            # Train a Random Forest model
            model = RandomForestClassifier(n_estimators = self.n_estimators, random_state=i)
            model.fit(X_sub, y_sub)

            # Store the model and selected features
            self.models.append(model)
            self.selected_features.append(col_indices)

    def predict(self, X):
        predictions = np.zeros((self.n_models, X.shape[0]))

        # Each model makes predictions based on its selected features
        for i, model in enumerate(self.models):
            X_sub = X[:, self.selected_features[i]]
            predictions[i] = model.predict_proba(X_sub)[:, 1]

        # Average predictions across models
        average_predictions = np.mean(predictions, axis=0)
        return average_predictions

lr_ensemble = joblib.load("/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel/lr_ensemble.pkl")
rf_ensemble = joblib.load("/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel/rf_ensemble.pkl")

# Make predictions using the loaded models
lr_predictions = lr_ensemble.predict(X_test_normalized)
rf_predictions = rf_ensemble.predict(X_test_normalized)

# Threshold evaluation
thresholds = [i / 10 for i in range(1, 10)]
flag_percentages = [i / 10 for i in range(1, 10)]  # Second parameter: percentage threshold

# Iterate over both thresholds and flag percentages
for threshold in thresholds:
    for flag_percentage in flag_percentages:
        # Get flags from both models
        lr_flags = (lr_predictions >= threshold).astype(int)
        rf_flags = (rf_predictions >= threshold).astype(int)

        # Calculate the overall percentage of flags for each instance
        combined_flags = np.vstack((lr_flags, rf_flags)).T
        overall_flag_percentage = np.mean(combined_flags, axis=1)

        # Final flag is 1 if overall_flag_percentage >= flag_percentage
        final_predictions = (overall_flag_percentage >= flag_percentage).astype(int)

        # Evaluate the combined ensemble
        cm = confusion_matrix(test_pred_data['Refi_flag'], final_predictions)
        TN, FP, FN, TP = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
        accuracy = accuracy_score(test_pred_data['Refi_flag'], final_predictions)
        precision = precision_score(test_pred_data['Refi_flag'], final_predictions, zero_division=0)
        recall = recall_score(test_pred_data['Refi_flag'], final_predictions, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)  # Modified Specificity
        f1 = f1_score(test_pred_data['Refi_flag'], final_predictions, zero_division=0)

        # Print metrics for the current threshold and flag percentage
        print(f"Threshold: {threshold}, Flag Percentage: {flag_percentage}")
        print(f"Confusion Matrix:\n{cm}")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"Specificity: {specificity:.4f}")
        print(f"F1 Score: {f1:.4f}")
        print("-" * 50)

# # Combine predictions and evaluate
# threshold = 0.2  # Example threshold
# flag_percentage = 0.7  # Example flag percentage
#
# lr_flags = (lr_predictions >= threshold).astype(int)
# rf_flags = (rf_predictions >= threshold).astype(int)
#
# combined_flags = np.vstack((lr_flags, rf_flags)).T
# overall_flag_percentage = np.mean(combined_flags, axis=1)
# final_predictions = (overall_flag_percentage >= flag_percentage).astype(int)
#
# test_pred_data['predictions'] = final_predictions

#
# # Evaluate the combined ensemble
# cm = confusion_matrix(test_pred_data['Refi_flag'], test_pred_data['predictions'])
# TN, FP, FN, TP = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
# accuracy = accuracy_score(test_pred_data['Refi_flag'], test_pred_data['predictions'])
# precision = precision_score(test_pred_data['Refi_flag'], test_pred_data['predictions'], zero_division=0)
# recall = recall_score(test_pred_data['Refi_flag'], test_pred_data['predictions'], zero_division=0)
# specificity = (TP + FP) / (TN + TP + FP + FN)  # TN / (TN + FP) if (TN + FP) != 0 else 0
#
# f1 = f1_score(test_pred_data['Refi_flag'], test_pred_data['predictions'], zero_division=0)
#
# # Print evaluation metrics
# print("Evaluation Metrics:")
# print(f"Confusion Matrix:\n{cm}")
# print(f"Accuracy: {accuracy:.4f}")
# print(f"Precision: {precision:.4f}")
# print(f"Recall: {recall:.4f}")
# print(f"specificity: {specificity:.4f}")
# print(f"F1 Score: {f1:.4f}")
