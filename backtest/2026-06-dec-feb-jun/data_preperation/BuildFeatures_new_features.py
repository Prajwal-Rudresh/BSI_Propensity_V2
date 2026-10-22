
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
from tqdm import tqdm
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta


warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199
pd.set_option('display.max_columns', None)

root_directory = './Input/'


def normalize_loan_number(series):
    """F19 backtest fix (2026-10-22): loan numbers as strings everywhere, never floats/ints,
    per CLAUDE.md's own code standard -- avoids dtype mismatches across join sites (main
    extract <-> MLW logins <-> credit bureau <-> payoff data <-> monthly label file). Strips
    whitespace; collapses a float-read artifact ("123.0") down to "123" without altering a
    genuine string value. Does not change any existing minus-sign-strip or similar
    transform already present in a caller -- this only fixes the end dtype.
    """
    s = series.astype(str).str.strip()
    float_like = s.str.match(r'^-?\d+\.0$')
    return s.where(~float_like, s.str.replace(r'\.0$', '', regex=True))


# Function to load and preprocess the MCK OneOff data
def load_and_preprocess_mck_data(file_path, date_column, date_format='mixed', chunk_size=100000):
    """Loads and preprocesses MCK OneOff data in chunks to reduce memory usage."""
    # Read file in chunks
    chunks = []
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        # Filter to keep only CURRENT status rows
        chunk = chunk[chunk.DLQ_Status == 'CURRENT']

        # F19 fix: loan number as string from the moment it's read, not int64.
        chunk['LoanNumber'] = normalize_loan_number(chunk['LoanNumber'])

        # Convert the date column to datetime
        chunk[date_column] = pd.to_datetime(chunk[date_column], format=date_format)

        # Extract Year-Month from the date
        chunk['Year_Month_Obs'] = chunk[date_column].dt.strftime('%Y-%m')

        # Append to list of chunks
        chunks.append(chunk)

        # Force garbage collection to free memory
        gc.collect()

    # Combine all chunks
    if chunks:
        df = pd.concat(chunks, ignore_index=True)
        # F5 fix (2026-10-22, needs-signoff): calculate_flags() does a trailing-6-month
        # self-merge per loan. It used to run INSIDE the per-chunk loop above, so a loan's
        # own history (split across many 100k-row chunks by file position, not by loan) was
        # never visible to its own self-merge -- Flag_Trailing_DaysDiff_GT45 was structurally
        # guaranteed to be 0 for every loan. Now runs once on the full, combined, loan-complete
        # dataset instead.
        df = calculate_flags(df)
        return df
    else:
        print("Warning: No data met the filtering criteria")
        return pd.DataFrame()


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
        'TermOfLoan', 'RemainingTerm', 'Year_Month_Obs', 'PropertyZipCode', 'PropertyState', 'MailingZip',
        'FICO_Difference', 'EscrowPayment_Flag', 'Flag_Trailing_DaysDiff_GT45'

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
        'Date_Paid_Off': ['Date Paid Off', 'DatePaidOff'],
        'Reason_Closed_Redifn': ['Reason Closed_Redifn','Reason Closed_Redfin'],
        'Reason_Closed': ['Reason Closed','ReasonClosed'],
        'Note_Rate': ['Note Rate','InterestRate'],
        'UPB_At_Payoff': ['UPB At Payoff', 'UPB At  Payoff','UPBAtPayoff'],
        'Original_Value': ['Original Value', 'Original  Value','OriginalBalance'],
        'Current_Value': ['Current Value','CurrentValue'],
        'Current_LTV_%': ['Current LTV % ', 'Current LTV %','Current_LTV_'],
        'Original_LTV_%': ['Original LTV % ', 'Original LTV %','Original_LTV_'],
        'Term_of_Loan': ['Term of Loan','TermofLoan'],
        'Remaining_Term': ['Remaining Term', 'Remaining  Term','RemainingTerm'],
        'Investor': ['Investor','ClientNameShort'],
        'Seller': ['Seller'],
        'Credit_Score': ['Credit Score','CreditScore']
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

    data.reset_index(inplace=True)
    data["Loan_Number"] = normalize_loan_number(data["Loan_Number"])  # F19 fix: was astype("int64")

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
    init_ln = mck_oneoff_data.shape[0]
    payoff_reason_data['Refinance_Sold_Flag'] = 1
    # Merge the two datasets on LoanNumber
    merged_data = mck_oneoff_data.merge(
        payoff_reason_data,
        how="left",
        left_on="LoanNumber",
        right_on="Loan_Number",
        validate="one_to_one",  # F19 fix: both sides confirmed unique per loan on real data
    )

    merged_data['Refinance_Sold_Flag'] = merged_data['Refinance_Sold_Flag'].fillna(0)

    # Convert 'Date_Paid_Off' to datetime and format to 'YYYY-MM'
    merged_data["Date_Paid_Off"] = pd.to_datetime(merged_data["Date_Paid_Off"], errors="coerce")
    merged_data["Date_Paid_Off"] = merged_data["Date_Paid_Off"].dt.strftime("%Y-%m")

    # F14/F22 fix (2026-10-22, needs-signoff, Option A): the old code defaulted every
    # non-matched (non-refi) loan's Event_Date to the hardcoded literal "2023-08", so
    # ~97%+ of training rows looked up the June 2023 market rate regardless of real
    # observation month. For a matched (real refi) loan: Interest_Rate_Date = its real
    # payoff date minus 2 months (unchanged -- this part was never broken). For a
    # non-matched loan: Interest_Rate_Date = that loan's own Year_Month_Obs directly, no
    # offset -- matches the scoring side's own fallback exactly (PredictionDataPreperation.py
    # never calls this function; bucket_and_transform_data()'s fallback already does this),
    # so the same loan gets the same rate-lookup convention in training and at scoring time.
    matched_date = pd.to_datetime(merged_data["Date_Paid_Off"], format="%Y-%m", errors="coerce")
    event_based_rate_date = (matched_date - pd.DateOffset(months=2)).dt.strftime("%Y-%m")
    own_month_rate_date = pd.to_datetime(merged_data["Year_Month_Obs"], format="%Y-%m").dt.strftime("%Y-%m")
    merged_data["Interest_Rate_Date"] = event_based_rate_date.fillna(own_month_rate_date)

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
        'FICO_Difference', 'EscrowPayment_Flag', 'Flag_Trailing_DaysDiff_GT45',
        'Refinanced_3_months_lookahead', 'Refinance_Sold_Flag'
    ]

    processed_data = merged_data[final_columns]

    print(f"Merged Data Shape: {processed_data.shape}")
    assert init_ln == processed_data.shape[0], f"Loan numbers didn't match after merging with payoffs"
    print("loan numbers after payoff merge: "+str(processed_data.shape[0]))

    return processed_data

def clamp_year_month_to_available(loan_df, rate_matrix, year_col="Year", month_col="Month"):
    """Backtest adapter (F32, 2026-10-22) -- NOT part of the original legacy code.

    The real interest-rate matrix has a ~2-month vendor feed lag (confirmed: covers through
    April 2026, nothing for May/June 2026). Scoring a later month than the matrix covers means
    the join (and its group-means fallback, keyed the same way) finds nothing, so
    Interest_Delta_Current_Market comes back null for every loan -- confirmed by an actual
    production-style run, not just theory. Per Prajwal's decision: for any loan whose own
    (Year, Month) is later than the latest month actually present in the rate matrix, carry
    forward the matrix's most recent available month as a proxy. A loan within the matrix's
    covered range is untouched. Returns a copy with Year/Month replaced only where needed --
    callers should merge on the returned columns, not the loan's original Year/Month.
    """
    loan_df = loan_df.copy()
    max_year, max_month = rate_matrix[[year_col, month_col]].drop_duplicates().sort_values(
        [year_col, month_col]
    ).iloc[-1]
    too_new = (loan_df[year_col] > max_year) | (
        (loan_df[year_col] == max_year) & (loan_df[month_col] > max_month)
    )
    loan_df.loc[too_new, year_col] = max_year
    loan_df.loc[too_new, month_col] = max_month
    return loan_df


def bucket_and_transform_data(data):
    """
    Apply bucketing for FICO scores, Current LTV, and compute additional fields like Year, Month, and Term.
    """
    # Convert Interest_Rate_Date to Year and Month
    init_ln = data.shape[0]
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

    assert init_ln == data.shape[0], f"Loan numbers didn't match after bucketing"
    print("loan numbers after bucketing: " + str(data.shape[0]))

    return data


def transform_credit_report_to_time_series(BSI_CreditReporting, Year_Month_Obs=None):
    print("After implementing CB_RPTD_STA, CB_RPTG_STA and CLOSE_CD_DB000 check")
    filtered_df = BSI_CreditReporting.copy()
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


def load_preaggregated_credit_report(file_path, snapshot_column):
    """Backtest adapter (2026-06-dec-feb-jun) -- NOT part of the original legacy code.

    The real credit-bureau extract for this backtest is a single pre-aggregated column
    per loan (e.g. CREDIT_BUREAU_PAYMENT_HISTORY_2026_JUNE), not the 36-raw-monthly-column
    layout process_credit_report()/transform_credit_report_to_time_series() expect -- that
    code path cannot run against this file's shape at all (see data/real/MANIFEST.md
    "Resolved decisions", and known-findings.md F13/F24, reclassified not-applicable for
    this dataset). This reads the real file directly and returns it in the same
    ['LoanNumber', 'CBH'] shape the rest of the pipeline already expects from
    process_credit_report(), so no downstream code changes beyond this one call site.
    """
    df = pd.read_csv(file_path) if str(file_path).lower().endswith(".csv") else pd.read_excel(file_path)
    out = df[["ACCT_NBR", snapshot_column]].rename(
        columns={"ACCT_NBR": "LoanNumber", snapshot_column: "CBH"}
    )
    out["LoanNumber"] = normalize_loan_number(out["LoanNumber"])  # F19 fix
    return out


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
    logins['LoanNumberPlain'] = normalize_loan_number(logins['LoanNumberPlain'])  # F19 fix: was astype(int)
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
    - The function uses pandas groupby instead of SQL to reduce memory usage
    - The generated DataFrame includes counts of logins grouped by
      LoanNumberPlain and Login_Year_Month.
    - The function also prints a message indicating that the monthly login count
      has been generated.
    """
    # Process in chunks to reduce memory usage
    chunk_size = 100000
    result_chunks = []

    # If the dataframe is large, process in chunks
    if len(Logins) > chunk_size:
        # Get unique combinations of LoanNumberPlain and Login_Year_Month
        for chunk_start in range(0, len(Logins), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(Logins))
            chunk = Logins.iloc[chunk_start:chunk_end]

            # Use pandas groupby which is more memory efficient than sqldf
            chunk_counts = chunk.groupby(['LoanNumberPlain', 'Login_Year_Month']).size().reset_index(name='Login_Count')
            result_chunks.append(chunk_counts)

            # Force garbage collection
            import gc
            gc.collect()

        # Combine all chunks and aggregate counts for duplicate groups
        if result_chunks:
            Monthly_Login_Count = pd.concat(result_chunks, ignore_index=True)
            # In case there are duplicates across chunks
            Monthly_Login_Count = Monthly_Login_Count.groupby(['LoanNumberPlain', 'Login_Year_Month'])['Login_Count'].sum().reset_index()
    else:
        # For smaller dataframes, process all at once
        Monthly_Login_Count = Logins.groupby(['LoanNumberPlain', 'Login_Year_Month']).size().reset_index(name='Login_Count')

    print('>>>>> Monthly Login Count Generated <<<<<<')
    return Monthly_Login_Count

def add_fips_to_training_oneoff(training_oneoff, Zip_fips_lookup):
    init_ln = training_oneoff.shape[0]
    # Convert PropertyZipCode to string
    training_oneoff['PropertyZipCode'] = training_oneoff['PropertyZipCode'].astype(str)

    # Remove decimal point and trailing zeros (e.g., "89014.0" -> "89014")
    training_oneoff['PropertyZipCode'] = training_oneoff['PropertyZipCode'].str.split('.').str[0]

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

    Zip_fips_lookup = Zip_fips_lookup.drop_duplicates(subset=['ZIP'], keep='first')


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

    assert init_ln == merged_df.shape[0], f"Loan numbers didn't match after merging with fips   "
    print("loan numbers after adding fips: " + str(merged_df.shape[0]))

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


def calculate_flags(df, date_col='Year_Month_Obs', loan_col='LoanNumber', fico_col='FICO_Score',
                    escrow_col='EscrowPayment', payment_date_col='DateLastPayment'):
    """
    Calculate various flags, including:
    - FICO score difference within the last 6 months.
    - EscrowPayment flag for comparison with payments 6 months ago.
    - A flag for gaps in DateLastPayment > 45 days in the trailing 6 months.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        date_col (str): The name of the column with dates (should be in datetime format).
        loan_col (str): The name of the column with loan numbers.
        fico_col (str): The name of the column with FICO scores.
        escrow_col (str): The name of the column with escrow payments.
        payment_date_col (str): The name of the column with the last payment date.

    Returns:
        pd.DataFrame: Original DataFrame with added flags and calculated columns.
    """
    # Ensure date columns are in datetime format
    df[date_col] = pd.to_datetime(df[date_col])
    df[payment_date_col] = pd.to_datetime(df[payment_date_col])

    # Sort the DataFrame by loan number and date
    df = df.sort_values(by=[loan_col, date_col]).reset_index(drop=True)

    # Calculate Days_Diff (difference in days between consecutive payments)
    df['Days_Diff'] = df.groupby(loan_col)[payment_date_col].diff().dt.days

    # Create a temporary DataFrame with relevant columns
    temp = df[[loan_col, date_col, fico_col, escrow_col, 'Days_Diff']]

    # Self-merge to find pairs within 6 months
    merged = temp.merge(
        temp,
        on=loan_col,
        suffixes=('', '_past')
    )

    # Filter rows where the past observation is within the trailing 6 months
    merged = merged[
        (merged[date_col] > merged[f'{date_col}_past']) &  # Past date must be before current date
        (merged[date_col] - merged[f'{date_col}_past'] <= pd.Timedelta(days=180))  # Within 6 months
    ]

    # Sort to prioritize the oldest date within the 6-month window
    merged = merged.sort_values(by=[loan_col, date_col, f'{date_col}_past'], ascending=[True, True, True])

    # Drop duplicates to retain the oldest valid observation for each date
    latest_scores = merged.drop_duplicates(subset=[loan_col, date_col], keep='first')

    # Calculate the FICO score difference
    latest_scores['FICO_Difference'] = latest_scores[fico_col] - latest_scores[f'{fico_col}_past']

    # Create the EscrowPayment flag
    latest_scores['EscrowPayment_Flag'] = (latest_scores[escrow_col] > latest_scores[f'{escrow_col}_past']).astype(int)

    # Group by current observations to aggregate trailing Days_Diff values
    trailing_values = merged.groupby([loan_col, date_col])['Days_Diff_past'].apply(list).reset_index()

    # Merge the differences, flags, and trailing Days_Diff back to the original DataFrame
    result = df.merge(
        latest_scores[[loan_col, date_col, 'FICO_Difference', 'EscrowPayment_Flag']],
        on=[loan_col, date_col],
        how='left'
    ).merge(
        trailing_values,
        on=[loan_col, date_col],
        how='left'
    )

    # Fill NaN differences, flags, and trailing values where no past data is available
    result['FICO_Difference'] = result['FICO_Difference'].fillna(0)
    result['EscrowPayment_Flag'] = result['EscrowPayment_Flag'].fillna(0).astype(int)
    result['Days_Diff_past'] = result['Days_Diff_past'].apply(lambda x: x if isinstance(x, list) else [])

    # Create the flag for trailing Days_Diff > 45
    result['Flag_Trailing_DaysDiff_GT45'] = result['Days_Diff_past'].apply(
        lambda x: 1 if any(val > 45 for val in x) else 0
    )

    # Rename the trailing column for clarity
    result.rename(columns={'Days_Diff_past': 'Trailing_6Months_DaysDiff'}, inplace=True)
    result.drop(columns=['Days_Diff', 'Trailing_6Months_DaysDiff'], inplace = True )

    return result



if __name__ == "__main__":
    print("done")