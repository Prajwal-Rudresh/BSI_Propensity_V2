import os
import numpy as np
import pandas as pd
import math
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from data_preperation.BuildFeatures_new_features import process_mck_oneoff_data, process_all_files, filter_and_clean_final_data, \
                          merge_and_process_data, bucket_and_transform_data, process_credit_report, \
                          transform_credit_report_to_time_series, rename_and_transform_logins_columns, \
                          count_monthly_logins, add_fips_to_training_oneoff, clean_domographic, \
                          load_preaggregated_credit_report

# Retrieve parameters from command-line arguments
#params = json.loads(sys.argv[1])
print(sys.argv[1])
params = json.loads(sys.argv[1])
st_date = params["st_date"]
end_date = params["end_date"]
data_universe = params["data_universe"]
test_date = params["test_date"]

if data_universe == 'fha':
    bucket = ["FHA", "VA"]
elif data_universe == 'conventional':
    bucket = ["CONVENTIONAL", "PMI"]


# st_date = "2024-10"
# end_date = "2024-10"
# data_universe = "conventional"
# test_date ="2024-11"

#if data_universe == 'fha':
#    bucket = ["FHA", "VA"]
#elif data_universe == 'conventional':
#    bucket = ["CONVENTIONAL", "PMI"]


# st_date = "2023-05"
# end_date = "2024-05"
# test_date = "2024-06"
# data_universe = 'conventional'
# if data_universe == 'fha':
#     bucket = ["FHA", "VA"]
# elif data_universe == 'conventional':
#     bucket = ["CONVENTIONAL"]

files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_directory = os.path.join(files_path, "inference_data")
month_of_interest = test_date

mck_file_path = os.path.join(root_directory, 'one_off_oct23_to_Feb25.csv')
processed_mck_data = process_mck_oneoff_data(mck_file_path, month_of_interest, month_of_interest)

print('>>>>> McK_Oneoff data processed <<<<<<')

# payoff_reason_data_path = os.path.join(root_directory, 'Payoffs Reasons')
# all_payoff_reason_data = process_all_files(payoff_reason_data_path)
# all_payoff_reason_data = filter_and_clean_final_data(all_payoff_reason_data)
# all_payoff_reason_data['Refinance_Sold_Flag']=1
# mck_oneoff_specific_column = merge_and_process_data(processed_mck_data, all_payoff_reason_data)
mck_oneoff_specific_column = processed_mck_data
mck_oneoff_specific_column = bucket_and_transform_data(mck_oneoff_specific_column)
mck_oneoff_final_df = mck_oneoff_specific_column  #[['LoanNumber', 'LoanType', 'Year', 'Month', 'Term', 'FICO', 'LTV']]
mck_oneoff_final_df[["Year", "Month", "Term"]] = mck_oneoff_final_df[["Year", "Month", "Term"]].apply(pd.to_numeric)

# Load and preprocess interest rate matrix
ir_file_path = os.path.join(root_directory, 'Interest Rate Data.xlsx')
interest_rate_matrix = pd.read_excel(ir_file_path)

interest_rate_matrix['Term'] = np.where(interest_rate_matrix['Term'] == '15 Year', 15, 30)
interest_rate_matrix.rename(columns={'Product': 'LoanType', 'ficorange': 'FICO', 'ltvrange': 'LTV', 'avg(rate)': 'Avg_Rate'}, inplace=True)
interest_rate_matrix['LoanType'] = interest_rate_matrix['LoanType'].str.upper()
interest_rate_matrix = interest_rate_matrix[['LoanType', 'Year', 'Month', 'Term', 'FICO', 'LTV', 'Avg_Rate']]


# Merge datasets on keys
merged_data = mck_oneoff_final_df.merge(
    interest_rate_matrix,
    how='left',
    on=['LoanType', 'Year', 'Month', 'Term', 'FICO', 'LTV']
)

# Drop duplicates
merged_data.drop_duplicates(inplace=True)

# Fill missing Avg_Rate values with group means
group_means = interest_rate_matrix.groupby(['LoanType', 'Year', 'Month', 'Term', 'FICO'])['Avg_Rate'].mean().reset_index()
merged_data = merged_data.merge(group_means, how='left', on=['LoanType', 'Year', 'Month', 'Term', 'FICO'], suffixes=('', '_Mean'))

# Fill missing interest rates
merged_data['Orginal_Interest_Rate'] = merged_data['Avg_Rate'].fillna(merged_data['Avg_Rate_Mean'])

impute_values = dict(merged_data.groupby("LoanType")["Orginal_Interest_Rate"].mean())
impute_values = {
    key: (np.round(impute_values['CONVENTIONAL'],5) if isinstance(value, float) and math.isnan(value) else np.round(value,5))
    for key, value in impute_values.items()
}

# Special handling for specific Loan Types
merged_data['Orginal_Interest_Rate'] = np.where(
    merged_data['LoanType'] == "PMI",
    impute_values['PMI'],
    merged_data['Orginal_Interest_Rate']
)
merged_data['Orginal_Interest_Rate'] = np.where(
    merged_data['LoanType'] == "CONVENTIONAL",
    impute_values['CONVENTIONAL'],
    merged_data['Orginal_Interest_Rate']
)

# Final dataset
# final_interest_rate = merged_data[['LoanNumber', 'LoanType', "Year", "Month", "Term", "FICO", "LTV", "Orginal_Interest_Rate"]]

# Backtest adapter: real file is a single pre-aggregated column, not the wide BSI_CREDITREPORTING.xlsx
# layout -- see load_preaggregated_credit_report() docstring and data/real/MANIFEST.md.
credit_report_file_path = os.path.join(files_path, "data", "real", "credit_bureau", "Credit Bureau Data.csv")
CREDIT_SNAPSHOT_COLUMN = "CREDIT_BUREAU_PAYMENT_HISTORY_2026_JUNE"
credit_report = load_preaggregated_credit_report(credit_report_file_path, CREDIT_SNAPSHOT_COLUMN)

logins_df = pd.read_csv(root_directory+'/MLW_logins.csv')
Logins = rename_and_transform_logins_columns(logins_df)
Monthly_Login_Count = count_monthly_logins(Logins)
Monthly_Login_Count['LoanNumberPlain']=Monthly_Login_Count['LoanNumberPlain'].astype(str).str.replace(r'^-','',regex=True).astype(int)
Monthly_Login_Count['Login_Year_Month'] = pd.to_datetime(Monthly_Login_Count['Login_Year_Month'])

files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
zips = pd.read_csv(os.path.join(files_path, "data_preperation", "Input", "Zip_FIPS_Mapping.csv"))
Training_Oneoff_Data_Record = add_fips_to_training_oneoff(merged_data, zips)

demographics = pd.read_csv(os.path.join(files_path, "data_preperation", "Input", "Census_Demographic.csv"))
purchase_index = pd.read_excel(os.path.join(files_path, "data_preperation", "Input", "HPI.xlsx"))

demographics = clean_domographic(demographics)
purchase_index['Year_Month_Index'] = pd.to_datetime(purchase_index['Year_Month_Index'])
Training_Oneoff_Data_Record=Training_Oneoff_Data_Record.merge(demographics, how='left',left_on=['FIPS'],right_on=['geography'])
Training_Oneoff_Data_Record=Training_Oneoff_Data_Record.merge(purchase_index, how='left',left_on=['Year_Month_Obs','PropertyState'],right_on=['Year_Month_Index','state'])


Training_Oneoff_Data_Record.rename(columns = {'CBH':'CREDIT_BUREAU_PAYMENT_HISTORY'}, inplace = True)
Training_Oneoff_Data_Record['Is_MailingZip_Equal_PropZip']=(Training_Oneoff_Data_Record['PropertyZipCode'].
                                                            astype(str)==Training_Oneoff_Data_Record['MailingZip'].
                                                            astype(str).apply(lambda x: x[:6])).astype(int)
Training_Oneoff_Data_Record['Interest_Delta_Current_Orginal']=(Training_Oneoff_Data_Record['InterestRate']-
                                                               Training_Oneoff_Data_Record['OriginalInterestRate']) # This features not used in model training, just for analysis to check.
Training_Oneoff_Data_Record['Interest_Delta_Current_Market']=(Training_Oneoff_Data_Record['InterestRate']-
                                             Training_Oneoff_Data_Record['Orginal_Interest_Rate'])
Training_Oneoff_Data_Record['Ltv_Delta_Orginal_Current']=(Training_Oneoff_Data_Record['Original_Ltv_Calc']-
                                         Training_Oneoff_Data_Record['CurrentLTV'])
Training_Oneoff_Data_Record=Training_Oneoff_Data_Record.merge(credit_report, how='left',left_on=['LoanNumber'],right_on=['LoanNumber'])
Training_Oneoff_Data_Record = Training_Oneoff_Data_Record.merge(Monthly_Login_Count, how='left',left_on=['LoanNumber','Year_Month_Obs'],right_on=['LoanNumberPlain','Login_Year_Month'])
Training_Oneoff_Data_Record.rename(columns = {'CBH':'CREDIT_BUREAU_PAYMENT_HISTORY'}, inplace = True)
Training_Oneoff_Data_Record['CREDIT_BUREAU_PAYMENT_HISTORY']=Training_Oneoff_Data_Record['CREDIT_BUREAU_PAYMENT_HISTORY'].fillna(0)
Training_Oneoff_Data_Record=Training_Oneoff_Data_Record[["LoanNumber","LoanType","CREDIT_BUREAU_PAYMENT_HISTORY",
                                                        "PrincipalBalance","Is_MailingZip_Equal_PropZip","FICO_Score",
                                                        "CurrentLTV","Login_Count","Interest_Delta_Current_Market",
                                                         "Ltv_Delta_Orginal_Current", "PropertyState",
                                                        "FICO_Difference", "EscrowPayment_Flag",
                                                         "Flag_Trailing_DaysDiff_GT45",
                                                         "Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher",
                                                        "Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars",
                                                        "Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied"]]


# print(Training_Oneoff_Data_Record.head(5))
# Define the path for the new folder and the output file
output_folder = os.path.join(files_path, 'modeling_data')  # Use proper path joining
output_file = f'prediction_data_{end_date}.csv'  # Use f-string formatting
# Create the folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Save the dataset (assuming `merged_data` is the DataFrame you want to save)
Training_Oneoff_Data_Record.to_csv(os.path.join(output_folder, output_file), index=False)
print(f"Dataset saved to {os.path.join(output_folder, output_file)}")
