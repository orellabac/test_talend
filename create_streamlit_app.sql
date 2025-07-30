-- Create or refresh the Streamlit app
CREATE OR REPLACE STREAMLIT TALEND_ETL_TOOLING_SIS_0
FROM @{YOUR_STAGE_NAME_HERE} -- Replace with the stage name where the whl file is stored
MAIN_FILE = 'snowflake_streamlit.py' -- Keep this as the main file for the Streamlit app
QUERY_WAREHOUSE = '{YOUR_WAREHOUSE_NAME_HERE}'  -- Replace with your warehouse name
COMMENT = 'Talend ETL Acceleration Tool - Convert Talend jobs to Snowpark Python'
;