
import os
import numpy as np
import pandas as pd
import dateutil.relativedelta
import datetime
from datetime import date, datetime
import warnings
import functools
import gc
import math
import sqldf
from glob import iglob  # Global directory
from itertools import product
from typing import List, Tuple, Iterable
from tqdm import tqdm  # Show data processing bar
import re
import sys
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta


warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199
pd.set_option('display.max_columns', None)

root_directory = './Input/'


# Function to load and preprocess the MCK OneOff data
def load_and_preprocess_mck_data(file_path, date_column, date_format='mixed'):
    """Loads and preprocesses MCK OneOff data."""
    df = pd.read_csv(file_path)
    # Convert the date column to datetime
    df[date_column] = pd.to_datetime(df[date_column], format=date_format)
    # Extract Year-Month from the date
    df['Year_Month_Obs'] = df[date_column].dt.strftime('%Y-%m')
    # Reset index for clean processing
    return df.reset_index(drop=True)


# Function to filter data by date range
def filter_data_by_date_range(df, date_column, start_date, end_date):
    """Filters the DataFrame based on a date range."""
    df[date_column] = pd.to_datetime(df[date_column])  # Ensure column is datetime
    if start_date == end_date:
        return df[(df[date_column] == start_date)].reset_index(drop=True)
    else:
        return df[(df[date_column] > start_date) & (df[date_column] <= end_date)].reset_index(drop=True)


# Function to select relevant columns for analysis
def select_columns(df, columns):
    """Selects a subset of columns for analysis."""
    return df[columns]


# Main workflow
def process_mck_oneoff_data(file_path, start_date, end_date):
    """Complete workflow for processing MCK OneOff data."""
    # Load and preprocess the data
    mck_data = load_and_preprocess_mck_data(file_path, date_column='DataDate')

    # Filter data by date range (August 2022 to August 2023)
    mck_data_filtered = filter_data_by_date_range(
        mck_data, date_column='Year_Month_Obs', start_date = start_date, end_date = end_date)

    # Select relevant columns for analysis
    columns_of_interest = [
        'LoanNumber', 'LoanType', 'InterestRate', 'OriginalInterestRate',
        'FICO_Score', 'Original_Ltv_Calc', 'CurrentLTV', 'PrincipalBalance',
        'TermOfLoan', 'RemainingTerm', 'Year_Month_Obs', 'PropertyZipCode', 'PropertyState', 'MailingZip'

    ]
    mck_data_selected = select_columns(mck_data_filtered, columns_of_interest)
    mck_oneoff_extract_column_unique = mck_data_selected.sort_values(['Year_Month_Obs']).groupby(
        ['LoanNumber']).last().reset_index()

    print(f"Filtered Data Shape: {mck_oneoff_extract_column_unique.shape}")

    return mck_oneoff_extract_column_unique


def load_and_clean_file(file_path, final_columns=None):
    """
    Load and clean a single Excel file by matching and renaming columns dynamically.

    Args:
    - file_path (str): Path to the Excel file.
    - final_columns (dict): Dictionary of target column names as keys and possible source names as values.

    Returns:
    - pd.DataFrame: Cleaned DataFrame with uniform column names.
    """
    df = pd.read_excel(file_path)

    # Create a mapping of existing columns to target columns
    column_mapping = {}
    for target_col, possible_names in final_columns.items():
        for col in possible_names:
            if col in df.columns:
                column_mapping[col] = target_col
                break

    # Rename columns
    df = df.rename(columns=column_mapping)

    # Filter to keep only the target columns
    return df[list(final_columns.keys())]


def process_all_files(directory):
    """
    Process all files in a directory, dynamically handling columns.

    Args:
    - directory (str): Directory containing the Excel files.
    - final_columns (dict): Dictionary of target column names and possible source names.

    Returns:
    - pd.DataFrame: Combined DataFrame of all files.
    """
    all_data = []

    # Define target columns and possible source names
    final_columns = {
        'Loan_Number': ['Loan Number', 'LoanNumber'],
        'Date_Paid_Off': ['Date Paid Off'],
        'Reason_Closed_Redifn': ['Reason Closed_Redifn'],
        'Reason_Closed': ['Reason Closed'],
        'Note_Rate': ['Note Rate'],
        'UPB_At_Payoff': ['UPB At Payoff', 'UPB At  Payoff'],
        'Original_Value': ['Original Value', 'Original  Value'],
        'Current_Value': ['Current Value'],
        'Current_LTV_%': ['Current LTV % ', 'Current LTV %'],
        'Original_LTV_%': ['Original LTV % ', 'Original LTV %'],
        'Term_of_Loan': ['Term of Loan'],
        'Remaining_Term': ['Remaining Term', 'Remaining  Term'],
        'Investor': ['Investor'],
        'Seller': ['Seller'],
        'Credit_Score': ['Credit Score']
    }

    # Iterate through all files in the directory
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        # Process only Excel files
        if file_name.endswith(('.xlsx', '.xls')):
            try:
                # Process the file
                df = load_and_clean_file(file_path, final_columns=final_columns)
                all_data.append(df)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

    # Combine all data
    return pd.concat(all_data, axis=0, ignore_index=True) if all_data else pd.DataFrame()


def filter_and_clean_final_data(data):
    """
    Filter and clean the combined data as per the additional conditions.

    Args:
    - data (pd.DataFrame): Combined DataFrame.

    Returns:
    - pd.DataFrame: Cleaned DataFrame after filtering.
    """
    # Filter out rows where 'Reason_Closed' is 'REO' or 'SS'
    data = data[(data["Reason_Closed"] != "REO") & (data["Reason_Closed"] != "SS")]

    # Ensure 'Reason_Closed_Redifn' is string, lowercase, and stripped
    data['Reason_Closed_Redifn'] = data['Reason_Closed_Redifn'].astype(str)
    data['Reason_Closed_Redifn'] = data['Reason_Closed_Redifn'].str.lower()
    data['Reason_Closed_Redifn'] = data['Reason_Closed_Redifn'].str.strip()

    # Remove rows where 'Reason_Closed_Redifn' is 'nan'
    data = data[data['Reason_Closed_Redifn'] != 'nan']
    data = data[data["Reason_Closed_Redifn"].isin(["off market", "not found", "for rent",
                                                   "not available", "offmarket", "house for rent",
                                                   "rent"])]

    data.reset_index(inplace=True)
    data["Loan_Number"] = data["Loan_Number"].astype("int64")

    # Remove duplicates based on column 'LoanNumber' keeping the most recent Date_Paid_Off
    data = data.sort_values(by='Date_Paid_Off', ascending=False).drop_duplicates(subset='Loan_Number', keep='first')

    return data

def merge_and_process_data(mck_oneoff_data, payoff_reason_data):
    """
    Merges the MCK One-Off data with the Payoff Reasons data and processes date-related columns.

    Args:
    - mck_oneoff_data (pd.DataFrame): The unique MCK One-Off extract columns.
    - payoff_reason_data (pd.DataFrame): The cleaned Payoff Reasons DataFrame.

    Returns:
    - pd.DataFrame: Processed DataFrame with selected columns and computed date fields.
    """
    payoff_reason_data['Refinance_Sold_Flag'] = 1
    # Merge the two datasets on LoanNumber
    merged_data = mck_oneoff_data.merge(
        payoff_reason_data,
        how="left",
        left_on="LoanNumber",
        right_on="Loan_Number"
    )

    merged_data['Refinance_Sold_Flag'] = merged_data['Refinance_Sold_Flag'].fillna(0)

    # Convert 'Date_Paid_Off' to datetime and format to 'YYYY-MM'
    merged_data["Date_Paid_Off"] = pd.to_datetime(merged_data["Date_Paid_Off"], errors="coerce")
    merged_data["Date_Paid_Off"] = merged_data["Date_Paid_Off"].dt.strftime("%Y-%m")

    # Create 'Event_Date': fill missing 'Date_Paid_Off' with default and format
    merged_data["Event_Date"] = merged_data["Date_Paid_Off"].fillna("2023-08")
    merged_data["Event_Date"] = pd.to_datetime(merged_data["Event_Date"], format="%Y-%m")
    merged_data["Event_Date"] = merged_data["Event_Date"].dt.strftime("%Y-%m")

    # Calculate 'Interest_Rate_Date' (two months prior to 'Event_Date')
    merged_data["Interest_Rate_Date"] = pd.to_datetime(merged_data["Event_Date"], format="%Y-%m") - pd.DateOffset(
        months=2)
    merged_data["Interest_Rate_Date"] = merged_data["Interest_Rate_Date"].dt.strftime("%Y-%m")

    # Create the new column
    merged_data['Year_Month_Obs'] = pd.to_datetime(merged_data['Year_Month_Obs'])
    merged_data['Date_Paid_Off'] = pd.to_datetime(merged_data['Date_Paid_Off'])
    merged_data['Date_Diff_Days'] = (merged_data['Date_Paid_Off'] - merged_data['Year_Month_Obs']).dt.days

    # Step 2: Create the flag column based on the date difference
    merged_data['Refinanced_3_months_lookahead'] = np.where(
        (merged_data['Date_Diff_Days'] >= 0) & (merged_data['Date_Diff_Days'] <= 90), 1, 0
    )


    # Select final columns for output
    final_columns = [
        'LoanNumber', 'LoanType', 'InterestRate', 'OriginalInterestRate', 'FICO_Score',
        'Original_Ltv_Calc', 'CurrentLTV', 'TermOfLoan', 'RemainingTerm', 'Interest_Rate_Date',
        'Year_Month_Obs', 'PropertyZipCode', 'PropertyState', 'MailingZip', 'PrincipalBalance',
        'Refinanced_3_months_lookahead', 'Refinance_Sold_Flag'
    ]

    processed_data = merged_data[final_columns]

    print(f"Merged Data Shape: {processed_data.shape}")

    return processed_data

def bucket_and_transform_data(data):
    """
    Apply bucketing for FICO scores, Current LTV, and compute additional fields like Year, Month, and Term.
    """
    # Convert Interest_Rate_Date to Year and Month
    if 'Interest_Rate_Date' not in data.columns:
        data["Interest_Rate_Date"] = pd.to_datetime(data["Year_Month_Obs"], format='%Y-%m')

    data["Interest_Rate_Date"] = pd.to_datetime(data["Interest_Rate_Date"], format='%Y-%m')
    data['Year'] = data['Interest_Rate_Date'].dt.year
    data['Month'] = data['Interest_Rate_Date'].dt.month

    # Determine Term (30 or 15 years)
    data['Term'] = np.where((data['RemainingTerm'] / 12) > 18, 30, 15)

    def bucket_fico(score):
        """
        Assign a bucket to a FICO score.
        """
        if 0 <= score < 620:
            return "<620"
        elif 620 <= score < 640:
            return ">=620"
        elif 640 <= score < 660:
            return ">=640"
        elif 660 <= score < 680:
            return ">=660"
        elif 680 <= score < 700:
            return ">=680"
        elif 700 <= score < 720:
            return ">=700"
        elif 720 <= score < 740:
            return ">=720"
        elif 740 <= score < 760:
            return ">=740"
        elif 760 <= score < 780:
            return ">=760"
        elif score >= 780:
            return ">=780"
        else:
            return "Unknown"


    # Fill NaN values with the column's mean
    mean_value = data['FICO_Score'].mean()  # Calculate the mean, ignoring NaNs
    data['FICO_Score'] = data['FICO_Score'].fillna(mean_value)

    # Apply bucketing function
    data['FICO'] = data['FICO_Score'].apply(bucket_fico)

    def bucket_ltv(ltv):
        """
        Assign a bucket to a Current LTV value.
        """
        if 0 <= ltv <= 30:
            return "<=30"
        elif 30 < ltv <= 60:
            return "<=60"
        elif 60 < ltv <= 70:
            return "<=70"
        elif 70 < ltv <= 75:
            return "<=75"
        elif 75 < ltv <= 80:
            return "<=80"
        elif 80 < ltv <= 85:
            return "<=85"
        elif 85 < ltv <= 90:
            return "<=90"
        elif 90 < ltv <= 95:
            return "<=95"
        elif ltv > 95:
            return ">95"
        else:
            return "Unknown"

    # Fill NaN values with the column's mean
    mean_value = data['CurrentLTV'].mean()  # Calculate the mean, ignoring NaNs
    data['CurrentLTV'] = data['CurrentLTV'].fillna(mean_value)

    # Apply bucketing function
    data['LTV'] = data['CurrentLTV'].apply(bucket_ltv)

    return data


def transform_credit_report_to_time_series(BSI_CreditReporting, Year_Month_Obs=None):
    print("After implementing CB_RPTD_STA, CB_RPTG_STA and CLOSE_CD_DB000 check")
    filtered_df = BSI_CreditReporting.copy()
    print(filtered_df.shape)
    if not Year_Month_Obs:
        Year_Month_Obs = [
            '2023-01',
            '2023-02',
            '2023-03',
            '2023-04',
            '2023-05',
            '2023-06',
            '2023-07',
            '2023-08',
            '2023-09',
            '2023-10',
            '2023-11',
            '2023-12',
            '2022-01',
            '2022-02',
            '2022-03',
            '2022-04',
            '2022-05',
            '2022-06',
            '2022-07',
            '2022-08',
            '2022-09',
            '2022-10',
            '2022-11',
            '2022-12',
            '2021-01',
            '2021-02',
            '2021-03',
            '2021-04',
            '2021-05',
            '2021-06',
            '2021-07',
            '2021-08',
            '2021-09',
            '2021-10',
            '2021-11',
            '2021-12',
        ]

    All_LoanNumber = []
    All_Year_Month_Obs = []
    All_History = []
    for loan in filtered_df['ACCT_NBR']:
        History = filtered_df[filtered_df['ACCT_NBR'] == loan].iloc[:, -37:-1]
        LoanNumber = [loan] * 36
        x1 = LoanNumber
        x2 = Year_Month_Obs
        x3 = History.iloc[0, :].to_list()
        All_LoanNumber.extend(x1)
        All_Year_Month_Obs.extend(x2)
        All_History.extend(x3)

    data = {'LoanNumber': All_LoanNumber,
            'Year_Month_Obs': All_Year_Month_Obs,
            'CREDIT_BUREAU_PAYMENT_HISTORY': All_History}
    BSI_CreditReporting = pd.DataFrame()
    BSI_CreditReporting = pd.DataFrame(data)
    print('>>>>> Credit Report Transformed to Timeseries <<<<<<')
    return BSI_CreditReporting


def process_credit_report(file_path, transform_func):
    """
    Process the BSI Credit Reporting data into a summarized format.

    Args:
        file_path (str): Path to the Excel file containing the credit report data.
        transform_func (function): Function to transform credit report data into a time series.

    Returns:
        pd.DataFrame: A dataframe summarizing the credit bureau payment history.
    """
    # Load data
    bsi_credit_report = pd.read_excel(file_path)

    # Filter rows with 'CBR_LAST_REPORT_DATE' > '2022-01'
    yes_reportclosedate = bsi_credit_report[bsi_credit_report['CBR_LAST_REPORT_DATE'] > '2022-01'].reset_index()

    # Add start_date and end_date columns
    yes_reportclosedate['start_date'] = yes_reportclosedate.CBR_LAST_REPORT_DATE.apply(
        lambda x: dt.strptime(dt.strftime(x + relativedelta(months=-13), '%Y-%m'), '%Y-%m')
    )
    yes_reportclosedate['end_date'] = yes_reportclosedate.CBR_LAST_REPORT_DATE.apply(
        lambda x: dt.strptime(dt.strftime(x + relativedelta(months=-2), '%Y-%m'), '%Y-%m')
    )

    # Transform data to time series format
    BSI_CreditReporting_yesclosedate = transform_func(yes_reportclosedate)

    # Merge additional columns
    BSI_CreditReporting_yesclosedate_1 = BSI_CreditReporting_yesclosedate.merge(
        yes_reportclosedate[['ACCT_NBR', 'start_date', 'end_date']],
        how='left',
        left_on='LoanNumber',
        right_on='ACCT_NBR'
    )

    # Update 'CREDIT_BUREAU_PAYMENT_HISTORY' values
    valid_values = ['B', 'D', '.', 0, 1, 2, 3, 4, 5, 6, 'H']
    BSI_CreditReporting_yesclosedate_1['CREDIT_BUREAU_PAYMENT_HISTORY'] = np.where(
        BSI_CreditReporting_yesclosedate_1['CREDIT_BUREAU_PAYMENT_HISTORY'].isin(valid_values),
        BSI_CreditReporting_yesclosedate_1['CREDIT_BUREAU_PAYMENT_HISTORY'],
        0
    )

    # Convert 'Year_Month_Obs' to datetime format
    BSI_CreditReporting_yesclosedate_1['ymo'] = BSI_CreditReporting_yesclosedate_1['Year_Month_Obs'].apply(
        lambda x: dt.strptime(x, '%Y-%m')
    )

    # Filter rows based on 'ymo' within the 'start_date' and 'end_date' range
    BSI_CreditReporting_yesclosedate_1_ = BSI_CreditReporting_yesclosedate_1[
        (BSI_CreditReporting_yesclosedate_1['ymo'] >= BSI_CreditReporting_yesclosedate_1['start_date']) &
        (BSI_CreditReporting_yesclosedate_1['ymo'] <= BSI_CreditReporting_yesclosedate_1['end_date'])
        ]

    # Create 'CBH' column: 0 for specific categories, 1 otherwise
    BSI_CreditReporting_yesclosedate_1_['CBH'] = np.where(
        BSI_CreditReporting_yesclosedate_1_['CREDIT_BUREAU_PAYMENT_HISTORY'].isin(['B', 'D', '.', 0]),
        0,
        1
    )

    # Summarize CBH by LoanNumber
    BSI_CreditReporting_yesclosedate_final = BSI_CreditReporting_yesclosedate_1_[['LoanNumber', 'CBH']]
    BSI_CreditReporting_yesclosedate_final = BSI_CreditReporting_yesclosedate_final.groupby('LoanNumber').sum(
        'CBH').reset_index()

    return BSI_CreditReporting_yesclosedate_final



def rename_and_transform_logins_columns(logins):
    """
    Rename and transform columns in a DataFrame representing login data.

    Args:
        logins (pd.DataFrame): A DataFrame containing login data with columns 'LoanNumber' and 'Date'.

    Returns:
        pd.DataFrame: A DataFrame with columns renamed and additional columns added:
            - 'LoanNumberPlain': Renamed from 'LoanNumber'.
            - 'LoginDate': Converted to a datetime format from the original 'Date'.
            - 'Login_Year_Month': New column derived from 'LoginDate' with the format 'YYYY-MM'.

    Note:
        This function modifies the input DataFrame in place.
    """
    logins.rename(columns={'LoanNumber': 'LoanNumberPlain',
                           'Date': 'LoginDate'}, inplace=True)

    logins['LoginDate'] = pd.to_datetime(logins['LoginDate'], format='mixed')
    logins['Login_Year_Month'] = logins['LoginDate'].dt.strftime('%Y-%m')
    logins['LoanNumberPlain'] = logins['LoanNumberPlain'].astype(int)
    print('>>>>> Logins columns renamed and transformed <<<<<<')
    return logins


def count_monthly_logins(Logins):
    """
    Count the number of logins per month for each LoanNumberPlain.

    This function uses the variable 'Logins' to generate a DataFrame
    containing the counts of logins for each LoanNumberPlain in each Login_Year_Month.

    Returns:
    DataFrame: A DataFrame containing the columns 'LoanNumberPlain',
               'Login_Year_Month', and 'Login_Count' representing the monthly
               login counts.

    Note:
    - The 'Logins' variable is assumed to be available for SQL queries.
    - The generated DataFrame includes counts of logins grouped by
      LoanNumberPlain and Login_Year_Month.
    - The function also prints a message indicating that the monthly login count
      has been generated.
    """
    Monthly_Login_Count = sqldf.run('''
                                SELECT LoanNumberPlain, Login_Year_Month, count(Login_Year_Month) as Login_Count
                                FROM Logins
                                GROUP BY LoanNumberPlain,  Login_Year_Month
                                '''
                                    )
    print('>>>>> Monthly Login Count Generated <<<<<<')
    return Monthly_Login_Count

def add_fips_to_training_oneoff(training_oneoff, Zip_fips_lookup):
    # Convert PropertyZipCode to string
    training_oneoff['PropertyZipCode'] = training_oneoff['PropertyZipCode'].astype(str)

    # Extract the first part of the ZIP code (before '-')
    training_oneoff['PropertyZipCode'] = training_oneoff['PropertyZipCode'].str.split('-').str[0]

    # Check for invalid lengths (greater than 5 after cleaning)
    invalid_rows = training_oneoff[training_oneoff['PropertyZipCode'].str.len() > 5]

    if not invalid_rows.empty:
        print("Found rows with PropertyZipCode longer than 5 characters after cleaning:")
        print(invalid_rows)
        sys.exit(1)  # Exit the program

    # Standardize PropertyZipCode: Pad with zeros to ensure length 5, then convert to integer
    training_oneoff['PropertyZipCode'] = training_oneoff['PropertyZipCode'].str.zfill(5).astype(int)

    # Standardize ZIP in Zip_fips_lookup
    Zip_fips_lookup['ZIP'] = Zip_fips_lookup['ZIP'].astype(str).str.zfill(5).astype(int)
    Zip_fips_lookup['STCOUNTYFP'] = Zip_fips_lookup['STCOUNTYFP'].astype(str).str.zfill(5).astype(int)

    # Perform a left join to add FIPS
    merged_df = training_oneoff.merge(
        Zip_fips_lookup[['ZIP', 'STCOUNTYFP']],  # Only take relevant columns from lookup
        left_on='PropertyZipCode',  # Join on standardized PropertyZipCode
        right_on='ZIP',  # Join on standardized ZIP
        how='left'  # Keep all rows from training_oneoff
    )

    # Rename and clean up columns
    merged_df.rename(columns={'STCOUNTYFP': 'FIPS'}, inplace=True)
    merged_df.drop(columns=['ZIP'], inplace=True)  # Drop extra ZIP column from lookup

    # merged_df['FIPS'] = merged_df['FIPS'].astype(int)

    print('>>>>> FIPS Added to McK_Oneoff <<<<<<')
    return merged_df


def clean_domographic(Demographic, keep_only_needed_column=False):
    Demographic = Demographic.loc[:, ~Demographic.columns.str.contains('^Unnamed')]
    columns = [
        'code',
        'geography',
        'Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher',
        'Percent_VEHICLES_AVAILABLE_Occupied_housing_units_No_vehicles_available',
        'Percent_VEHICLES_AVAILABLE_Occupied_housing_units_1_vehicle_available',
        'Percent_VEHICLES_AVAILABLE_Occupied_housing_units_3_or_more_vehicles_available',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Agriculture_forestry_fishing_and_hunting_and_mining',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Construction',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Manufacturing',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Wholesale_trade',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Retail_trade',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Transportation_and_warehousing_and_utilities',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Information',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Finance_and_insurance_and_real_estate_and_rental_and_leasing',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Professional_scientific_and_management_and_administrative_and_waste_management_services',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Educational_services_and_health_care_and_social_assistance',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Arts_entertainment_and_recreation_and_accommodation_and_food_services',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Other_services_except_public_administration',
        'Percent_INDUSTRY_Civilian_employed_population_16_years_and_over_Public_administration',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_earnings',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Social_Security',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_retirement_income',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Supplemental_Security_Income',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_cash_public_assistance_income',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Food_Stamp_over_SNAP_benefits_in_the_past_12_months',
        'Percent_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Nonfamily_households',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Median_household_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_earnings_Mean_earnings_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Social_Security_Mean_Social_Security_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_retirement_income_Mean_retirement_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Supplemental_Security_Income_Mean_Supplemental_Security_Income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_cash_public_assistance_income_Mean_cash_public_assistance_income_dollars',
        'Percent_HEALTH_INSURANCE_COVERAGE_Civilian_noninstitutionalized_population_With_health_insurance_coverage_With_private_health_insurance',
        'Percent_HEALTH_INSURANCE_COVERAGE_Civilian_noninstitutionalized_population_With_health_insurance_coverage_With_public_coverage',
        'Percent_HEALTH_INSURANCE_COVERAGE_Civilian_noninstitutionalized_population_No_health_insurance_coverage',
        'Estimate_EMPLOYMENT_STATUS_Population_16_years_and_over',
        'Percent_EMPLOYMENT_STATUS_Population_16_years_and_over_In_labor_force',
        'Percent_EMPLOYMENT_STATUS_Civilian_labor_force_Unemployment_Rate',
        'Percent_SELECTED_MONTHLY_OWNER_COSTS_AS_A_PERCENTAGE_OF_HOUSEHOLD_INCOME_SMOCAPI_Housing_units_with_a_mortgage_excluding_units_where_SMOCAPI_cannot_be_computed_35_0_percent_or_more',
        'Percent_SELECTED_MONTHLY_OWNER_COSTS_AS_A_PERCENTAGE_OF_HOUSEHOLD_INCOME_SMOCAPI_Housing_unit_without_a_mortgage_excluding_units_where_SMOCAPI_cannot_be_computed_35_0_percent_or_more',
        'Percent_GROSS_RENT_AS_A_PERCENTAGE_OF_HOUSEHOLD_INCOME_GRAPI_Occupied_units_paying_rent_excluding_units_where_GRAPI_cannot_be_computed_35_0_percent_or_more',
        'Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied',
        'Percent_HOUSING_TENURE_Occupied_housing_units_Renter_occupied',
        'Percent_HOUSING_OCCUPANCY_Total_housing_units_Vacant_housing_units',
        'GINI_index',
        'Estimate_Median_gross_rent_as_a_percentage_of_household_income',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Median_household_income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_earnings_Mean_earnings_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Social_Security_Mean_Social_Security_income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_retirement_income_Mean_retirement_income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_Supplemental_Security_Income_Mean_Supplemental_Security_Income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_With_cash_public_assistance_income_Mean_cash_public_assistance_income_dollars_1',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Families_Median_family_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Families_Mean_family_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Per_capita_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Nonfamily_households_Median_nonfamily_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Nonfamily_households_Mean_nonfamily_income_dollars',
        'Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Median_earnings_for_workers_dollars'
    ]
    Demographic.columns = columns

    return Demographic


if __name__ == "__main__":
    print("done")