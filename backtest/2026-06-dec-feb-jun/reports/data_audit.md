# Data audit (aggregate-only, auto-generated)

## credit_bureau\Credit Bureau Data.csv
- rows: 111474
- columns (18): ['CLOSE_CD_DB000', 'ACCT_NBR', 'PRIM_BWRS_NM_DB001', 'CB_RPTG_STA', 'CBR_LAST_REPORT_DATE', 'CBR_RPTD_OPEND_DATE', 'CBR_RPTD_CLOSE_DATE', 'CBR_RPTD_LAST_PAYMENT_DATE', 'CB_RPTD_STA', 'CBR_COMMENT_CD', 'CB_RPT_CMNTS', 'CB_RPT_PMT_RT', 'CBR_RPTD_HIGH_AMOUNT', 'CBR_RPTD_PAYMENT_AMOUNT', 'CBR_RPTD_ACTUAL_PAYMENT_AMOUNT', 'CBR_RPTD_CURRENT_BALANCE', 'CREDIT_BUREAU_PAYMENT_HISTORY_2026_JUNE', 'DataDate']
- `CBR_LAST_REPORT_DATE` range: 2017-04-10 to 2026-10-10
- `CBR_RPTD_OPEND_DATE` range: 1997-07-31 to 2026-10-06
- `CBR_RPTD_CLOSE_DATE` range: 2022-01-06 to 2026-09-30
- `CBR_RPTD_LAST_PAYMENT_DATE` range: 2017-02-28 to 2026-09-30
- `DataDate` range: 2026-10-20 to 2026-10-20

## interest_rate\Interest Rate Data.xlsx
- rows: 8586
- columns (7): ['Product', 'Term', 'Year', 'Month', 'ficorange', 'ltvrange', 'avg(rate)']
- `Month` range: 1970-01-01 to 1970-01-01

## mlw_logins\MLW_logins.csv
- rows: 14122716
- columns (2): ['LoanNumber', 'Date']
- `Date` range: 2021-02-22 to 2026-10-04

## one_off\One Off Data Headers .xlsx
- rows: 48
- columns (1): ['LoanNumber']

## one_off\one_off_oct23_to_Feb25.csv
- rows: 4075644
- columns (49): ['LoanNumber', 'LoanType', 'PrincipalBalance', 'NextDueDate', 'InterestPaidToDate', 'DateLastPayment', 'InterestRate', 'OriginalInterestRate', 'PropertyAddressLine1', 'PropertyAddressLine2', 'PropertyCityName', 'PropertyState', 'PropertyZipCode', 'MailingAddLine1', 'MailingAddLine2', 'MailingCity', 'MailingState', 'MailingZip', 'FICO_Score', 'FicoDate', 'BankruptcyFlag', 'LossMitigationStatus', 'ForeclosureStatus', 'DLQ_Status', 'NoteDate', 'ServicingDate', 'TransferDate', 'PiPmt', 'EscrowPayment', 'EscrowBalance', 'ReportToCreditBureau', 'AppraisalDate', 'AppraisedAmount', 'Original_Ltv_Calc', 'CurrentLTV', 'PriorServicerName', 'InvestorOwner', 'AcquiredPortfolioName', 'PrimaryBorrowerOptOut', 'SecondaryBorrowerOptOut', 'TermOfLoan', 'RemainingTerm', 'FIXED ARM', 'SaleAmount', 'OriginalBalance', 'RawLeadType', 'ForbearanceFlag', 'PropMailAddressLine1Match', 'DataDate']
- `NextDueDate` range: 2007-10-01 to 2032-03-01
- `InterestPaidToDate` range: 2007-09-01 to 2032-02-01
- `DateLastPayment` range: 1982-02-22 to 2026-10-01
- `FicoDate` range: 1998-03-06 to 2026-09-30
- `NoteDate` range: 1994-03-10 to 2026-09-21
- `ServicingDate` range: 2001-11-30 to 2026-09-28
- `TransferDate` range: 1998-03-06 to 2026-09-30
- `AppraisalDate` range: 1994-03-01 to 2026-12-01
- `DataDate` range: 2023-09-30 to 2026-09-30

## payoff_data\Combined_Payoff_Data_with_RefinanceYes.xlsx
- rows: 3020
- columns (21): ['LoanNumber', 'DatePaidOff', 'UPBAtPayoff', 'ReasonClosed', 'Seller', 'LoanType', 'DLQ_StatusAtPayoff', 'InterestRate', 'OriginalBalance', 'CurrentValue', 'Current_LTV_', 'Original_LTV_', 'TermofLoan', 'RemainingTerm', 'ClientNameShort', 'CreditScore', 'SourceYear', 'Month', 'Reason Closed_Redfin', 'SoldDate', 'Refinance']
- `DatePaidOff` range: 2025-12-01 to 2026-08-03
- `Month` range: 1970-01-01 to 1970-01-01
- `SoldDate` range: could not parse as dates

## payoff_reason\PayoffReason2026-06.xlsx
- rows: 850
- columns (59): ['PayoffType', 'Pool', 'DatePaidOff', 'Loan Number', 'Reason Closed', 'Note Rate', 'UPB At  Payoff', 'Original  Value', 'Current Value', 'Current LTV % ', 'Original LTV % ', 'Term of Loan', 'Remaining  Term', 'Investor', 'Investor Code', 'Seller', 'Number of Visits (120Days Prior To Payoff)', 'Credit Score', 'Loan Type', 'Raw Lead File Assignment', 'Eligible For Refinance Indicator', 'Total Curtailment Applied', 'Servicing Date', 'Secondary Borrowers Home Phone', 'Secondary Cell Phone', 'Secondary Work Phone', 'Request Type', 'Did Originations Dept Open CIT 101', 'CIT 101 Date', 'Property Address Line1', 'Property Address Line2', 'Property City Name', 'Property State', 'Property Zip Code', 'Primary Borrower First Name', 'Primary Borrower Last Name', 'Co Borrower First Name', 'Co Borrower Last Name', 'Aggregate Monthly Payment Amountfor Open Trade', 'Agg Balance for all Revolving Trade exclude Secured Trade', 'Highest Balance for all Revolving Trade exclude Secured Trade', 'Number of Open Home Equity Trade Line', 'Home Value', 'Curr LTV', 'MSR SELLER', 'DLQ Status At Payoff', 'Probability To Refi', 'Probability To Sell', 'Note Date', 'Original Balance', 'Acq Name', 'Reason Closed_Redifn', 'Refi', 'Comments', "Sold June'26", 'In Velocify', 'Velocify Status', 'Velocify Comments', 'Updated Velocify Status']
- `DatePaidOff` range: 2026-06-01 to 2026-06-30
- `Servicing Date` range: 2013-01-14 to 2026-05-15
- `CIT 101 Date` range: 2022-06-30 to 2026-06-29
- `Aggregate Monthly Payment Amountfor Open Trade` range: 1970-01-01 to 1970-01-01
- `Note Date` range: 1998-06-22 to 2026-04-30
- `Updated Velocify Status` range: could not parse as dates

## payoff_reason\PayoffReason2026-07.xlsx
- rows: 840
- columns (59): ['PayoffType', 'Pool', 'DatePaidOff', 'Loan Number', 'Reason Closed', 'Note Rate', 'UPB At  Payoff', 'Original  Value', 'Current Value', 'Current LTV % ', 'Original LTV % ', 'Term of Loan', 'Remaining  Term', 'Investor', 'Investor Code', 'Seller', 'Number of Visits (120Days Prior To Payoff)', 'Credit Score', 'Loan Type', 'Raw Lead File Assignment', 'Eligible For Refinance Indicator', 'Total Curtailment Applied', 'Servicing Date', 'Secondary Borrowers Home Phone', 'Secondary Cell Phone', 'Secondary Work Phone', 'Request Type', 'Did Originations Dept Open CIT 101', 'CIT 101 Date', 'Property Address Line1', 'Property Address Line2', 'Property City Name', 'Property State', 'Property Zip Code', 'Primary Borrower First Name', 'Primary Borrower Last Name', 'Co Borrower First Name', 'Co Borrower Last Name', 'Aggregate Monthly Payment Amountfor Open Trade', 'Agg Balance for all Revolving Trade exclude Secured Trade', 'Highest Balance for all Revolving Trade exclude Secured Trade', 'Number of Open Home Equity Trade Line', 'Home Value', 'Curr LTV', 'MSR SELLER', 'DLQ Status At Payoff', 'Probability To Refi', 'Probability To Sell', 'Note Date', 'Original Balance', 'Acq Name', 'Reason Closed_Redifn', 'Refi', 'Comments', "Sold July'26", 'In Velocify', 'Velocify Status', 'Velocify Comments', 'Updated Velocify Status']
- `DatePaidOff` range: 2026-07-01 to 2026-07-31
- `Servicing Date` range: 2018-04-16 to 2026-06-22
- `CIT 101 Date` range: 2022-01-13 to 2026-07-31
- `Aggregate Monthly Payment Amountfor Open Trade` range: 1970-01-01 to 1970-01-01
- `Note Date` range: 2001-05-18 to 2026-04-30
- `Updated Velocify Status` range: could not parse as dates

## payoff_reason\PayoffReason2026-08.xlsx
- rows: 671
- columns (59): ['PayoffType', 'Pool', 'DatePaidOff', 'Loan Number', 'Reason Closed', 'Note Rate', 'UPB At  Payoff', 'Original  Value', 'Current Value', 'Current LTV % ', 'Original LTV % ', 'Term of Loan', 'Remaining  Term', 'Investor', 'Investor Code', 'Seller', 'Number of Visits (120Days Prior To Payoff)', 'Credit Score', 'Loan Type', 'Raw Lead File Assignment', 'Eligible For Refinance Indicator', 'Total Curtailment Applied', 'Servicing Date', 'Secondary Borrowers Home Phone', 'Secondary Cell Phone', 'Secondary Work Phone', 'Request Type', 'Did Originations Dept Open CIT 101', 'CIT 101 Date', 'Property Address Line1', 'Property Address Line2', 'Property City Name', 'Property State', 'Property Zip Code', 'Primary Borrower First Name', 'Primary Borrower Last Name', 'Co Borrower First Name', 'Co Borrower Last Name', 'Aggregate Monthly Payment Amountfor Open Trade', 'Agg Balance for all Revolving Trade exclude Secured Trade', 'Highest Balance for all Revolving Trade exclude Secured Trade', 'Number of Open Home Equity Trade Line', 'Home Value', 'Curr LTV', 'MSR SELLER', 'DLQ Status At Payoff', 'Probability To Refi', 'Probability To Sell', 'Note Date', 'Original Balance', 'Acq Name', 'Reason Closed_Redifn', 'Refi', 'Comments', "Sold July'26", 'In Velocify', 'Velocify Status', 'Velocify Comments', 'Updated Velocify Status']
- `DatePaidOff` range: 2026-08-03 to 2026-08-31
- `Servicing Date` range: 2014-07-11 to 2026-05-05
- `CIT 101 Date` range: 2024-01-11 to 2026-08-31
- `Aggregate Monthly Payment Amountfor Open Trade` range: 1970-01-01 to 1970-01-01
- `Note Date` range: 1999-02-12 to 2026-03-26
- `Updated Velocify Status` range: could not parse as dates
