create or replace procedure sp_unzip_whl_handler(
    source_stage VARCHAR,
    whl_filename VARCHAR,
    target_stage VARCHAR) 
returns Table() 
language python runtime_version=3.11 
packages=('snowflake-snowpark-python') 
handler='unzip_whl_handler' as '
import snowflake.snowpark as snowpark
import zipfile
import tempfile
import re
import os
import io
import sys
from snowflake.snowpark.functions import col
from snowflake.snowpark.files import SnowflakeFile
from snowflake.snowpark import Session

def unzip_whl_handler(session: Session, source_stage: str, whl_filename: str, target_stage: str = None):
    """
    Unzip a .whl file from an internal stage within Snowflake, reorganizing its contents
    to maintain ''talend_etl_tooling'' structure, extract ''data'' files to root,
    and omit ''dist-info'' folders.
    """
    try:
        if not source_stage.startswith(''@''):
            source_stage = f''@{source_stage}''
        if target_stage and not target_stage.startswith(''@''):
            target_stage = f''@{target_stage}''

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Downloading {whl_filename} from {source_stage} to {temp_dir}...")
            session.file.get(f"{source_stage}/{whl_filename}", temp_dir)
            local_file_path = os.path.join(temp_dir, whl_filename)

            if not os.path.exists(local_file_path):
                return f"ERROR: Failed to download {whl_filename} from {source_stage}"

            extract_dir = os.path.join(temp_dir, ''extracted_whl'')
            os.makedirs(extract_dir, exist_ok=True)

            print(f"Extracting {whl_filename} to {extract_dir}...")
            
            with zipfile.ZipFile(local_file_path, ''r'') as zip_ref:
                zip_ref.extractall(extract_dir)
            print("Extraction complete.")

            result_message = f"SUCCESS: Extracted {len(zip_ref.namelist())} files from {whl_filename} locally."

            if target_stage:
                uploaded_count = 0

                pattern = r''^([^-]+(?:-[^-]+)*?)-(\\d+(?:\\.\\d+)*(?:\\.(?:dev|a|b|rc)\\d*)?)-(.+)\\.whl$''

                prefix = ""
                
                match = re.match(pattern, whl_filename)
                if match:
                    prefix = match.group(1) + "-" + match.group(2)
                
                # Define expected paths within the extracted structure
                talend_etl_tooling_prefix = "talend_etl_tooling/"

                data_folder_prefix = f"{prefix}.data/data/"
                dist_info_prefix = f"{prefix}.dist-info/"

                print(f"Starting reorganization and upload to {target_stage}...")
                
                # Iterate over all files extracted to the temporary directory
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        rel_path_in_extracted = os.path.relpath(file_path, extract_dir)
                        
                        target_upload_path = None

                        if rel_path_in_extracted.startswith(talend_etl_tooling_prefix):
                            target_upload_path = os.path.join(target_stage, rel_path_in_extracted)
                        elif rel_path_in_extracted.startswith(data_folder_prefix):
                            target_filename = os.path.basename(file_path)
                            target_upload_path = os.path.join(target_stage, target_filename)
                        elif rel_path_in_extracted.startswith(dist_info_prefix):
                            pass
                        else:
                            if os.path.dirname(rel_path_in_extracted) == "": # File directly in the wheel''s root
                                target_upload_path = os.path.join(target_stage, rel_path_in_extracted)
                            else:
                                target_upload_path = os.path.join(target_stage, rel_path_in_extracted)

                        if target_upload_path:
                            try:
                                stage_put_dest_dir = os.path.dirname(target_upload_path)
                                if not stage_put_dest_dir:
                                    stage_put_dest_dir = target_stage
                                    
                                print(f"Uploading {file} to {stage_put_dest_dir}/...")
                                session.file.put(
                                    file_path,
                                    stage_put_dest_dir,
                                    auto_compress=False,
                                    overwrite=True
                                )
                                uploaded_count += 1
                            except Exception as upload_error:
                                result_message += f"\\nWarning: Failed to upload {rel_path_in_extracted} to {stage_put_dest_dir}: {str(upload_error)}"

                result_message += f"\\nReorganized and uploaded {uploaded_count} files to {target_stage}."

            all_extracted_paths = [os.path.relpath(os.path.join(root, file), extract_dir) for root, dirs, files in os.walk(extract_dir) for file in files]
            
            sample_files = all_extracted_paths[:5]
            result_message += f"\\nSample extracted files (from original wheel): {'', ''.join(sample_files)}"
            if len(all_extracted_paths) > 5:
                result_message += f" ... and {len(all_extracted_paths) - 5} more"

            return result_message

    except zipfile.BadZipFile:
        return f"ERROR: {whl_filename} is not a valid zip/whl file"
    except FileNotFoundError:
        return f"ERROR: File {whl_filename} not found in stage {source_stage}"
    except Exception as e:
        return f"ERROR: An unexpected error occurred: {str(e)}"'
;

call sp_unzip_whl_handler(
    source_stage=>'{YOUR_SOURCE_INTERNAL_STAGE_NAME_HERE}', -- Replace with the stage name where the whl file is stored
    whl_filename=>'{WHL_FILE_NAME_HERE}', -- Replace with the actual whl file name
    target_stage=>'{YOUR_TARGET_INTERNAL_STAGE_NAME_HERE}' -- Replace with the stage name where you want to store the extracted files
);