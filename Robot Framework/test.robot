*** Settings ***
Documentation     Data Quality validation test comparing HTML report table with partitioned Parquet dataset.
Library           SeleniumLibrary
Library           helper.py
Test Teardown     Close Browser

*** Variables ***
${REPORT_FILE}        ${CURDIR}/report.html
${PARQUET_FOLDER}     ${CURDIR}/parquet_data/facility_type_avg_time_spent_per_visit_date
${FILTER_DATE}        2026-09-26

*** Test Cases ***
Verify HTML Report Table Matches Parquet Dataset
    [Documentation]    Step-by-step verification of HTML report table data against partitioned Parquet dataset.
    # 1. Open report.html in Chrome
    Open Report In Chrome    ${REPORT_FILE}
    # 2. Locate the HTML table
    ${table}=    Locate HTML Table
    # 3. Read table data into DataFrame using helper function passing located table
    ${html_df}=    Read HTML Table Data    ${table}
    # 4. Read Parquet data and apply optional filtering using helper function
    ${parquet_df}=    Read Parquet Dataset    ${PARQUET_FOLDER}    ${FILTER_DATE}
    # 5. Compare both DataFrames: Pass if they match, Fail if mismatches are found
    Compare DataFrames    ${html_df}    ${parquet_df}

*** Keywords ***
Open Report In Chrome
    [Arguments]    ${file_path}
    Open Browser    file:///${file_path}    headlesschrome
    Set Window Size    1920    1080
    Wait Until Page Contains Element    xpath=//*[@class='table']    timeout=10s
    Wait Until Page Contains Element    css:.column-cell    timeout=10s

Locate HTML Table
    ${table}=    Get WebElement    xpath=//*[@class='table']
    RETURN    ${table}
