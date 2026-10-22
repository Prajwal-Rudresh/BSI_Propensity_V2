import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from imblearn.over_sampling import SMOTE
import joblib


# Define paths and load data
root_directory = "/Users/abhilashchenreddy/PycharmProjects/BSI/modeling_data"
training_path = os.path.join(root_directory, "training_data.csv")
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
data = data[data.LoanType.isin(['FHA', 'VA'])]

# One-hot encode categorical features
categorical_columns = data.select_dtypes(include=['object']).columns
data = pd.get_dummies(data, columns=categorical_columns, drop_first=True)

# Define features and target
X = data.drop(["Refinanced_3_months_lookahead"], axis=1)
y = data["Refinanced_3_months_lookahead"].astype(int)

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, stratify=y, test_size=0.2, random_state=0
)

# Impute missing values
imputer = SimpleImputer(strategy='mean')
X_train_imputed = imputer.fit_transform(X_train)
X_test_imputed = imputer.transform(X_test)

# Normalize the data
scaler = StandardScaler()
X_train_normalized = scaler.fit_transform(X_train_imputed)
X_test_normalized = scaler.transform(X_test_imputed)

# Resample training data to balance classes using SMOTE
smote = SMOTE(random_state=42, sampling_strategy=0.9)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train_normalized, y_train)

# Verify class balance
print(f"Class distribution after SMOTE: {np.bincount(y_train_resampled)}")

# Ensemble of Linear Regression Models
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


# Initialize and train the ensembles
lr_ensemble = LinearRegressionEnsemble(n_models=10, row_fraction=0.5, col_fraction=0.5)
rf_ensemble = RandomForestEnsemble(n_models=10, row_fraction=0.5, col_fraction=0.5, n_estimators=50)

lr_ensemble.fit(X_train_resampled, y_train_resampled)
rf_ensemble.fit(X_train_resampled, y_train_resampled)

# Predict on the test data
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
        cm = confusion_matrix(y_test, final_predictions)
        TN, FP, FN, TP = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
        accuracy = accuracy_score(y_test, final_predictions)
        precision = precision_score(y_test, final_predictions, zero_division=0)
        recall = recall_score(y_test, final_predictions, zero_division=0)
        specificity = (TP + FP) / (TN + TP + FP + FN)  # Modified Specificity
        f1 = f1_score(y_test, final_predictions, zero_division=0)

        # Print metrics for the current threshold and flag percentage
        print(f"Threshold: {threshold}, Flag Percentage: {flag_percentage}")
        print(f"Confusion Matrix:\n{cm}")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"Specificity: {specificity:.4f}")
        print(f"F1 Score: {f1:.4f}")
        print("-" * 50)

# Save the models, scaler, and imputer
save_path = "/Users/abhilashchenreddy/PycharmProjects/BSI/Modeling/BestModel"
os.makedirs(save_path, exist_ok=True)

joblib.dump(lr_ensemble, os.path.join(save_path, "lr_ensemble.pkl"))
joblib.dump(rf_ensemble, os.path.join(save_path, "rf_ensemble.pkl"))
joblib.dump(scaler, os.path.join(save_path, "scaler.pkl"))
joblib.dump(imputer, os.path.join(save_path, "imputer.pkl"))

print(f"Models, scaler, and imputer saved to {save_path}")