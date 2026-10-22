from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import json
import shutil
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import csv

app = Flask(__name__)

def log_model_run(status, data=None, prediction_file='', error_message='', model_results=None):
    try:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_log.csv')
        file_exists = os.path.exists(log_file)
        
        with open(log_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'status', 'st_date', 'end_date', 'test_date', 'data_universe', 'prediction_file', 'Recall', 'Specificity', 'error_message'])
            
            data = data or {}
            model_results = model_results or {}
            recall = model_results.get('recall', model_results.get('Recall', ''))
            specificity = model_results.get('specificity', model_results.get('Specificity', ''))
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status,
                data.get('st_date', ''),
                data.get('end_date', ''),
                data.get('test_date', ''),
                data.get('data_universe', ''),
                prediction_file,
                recall,
                specificity,
                error_message
            ])
    except Exception as e:
        print(f"Failed to write audit log: {e}")


@app.route('/')
def home():
    # Define source and destination paths using f-strings directly
    current_year_month = datetime.now().strftime("%Y-%m")
    source_file = "inference_data/Archive/PayoffReason2025-03.xlsx"
    destination_file = f"inference_data/PayoffReason{current_year_month}.xlsx"

    # Check if the current month's file exists, and create it if it doesn't
    if os.path.exists(source_file) and not os.path.exists(destination_file):
        try:
            shutil.copy2(source_file, destination_file)
            print(f"Created dummy file {destination_file} from archive")
        except Exception as e:
            print(f"Error copying file: {str(e)}")

    return render_template('index.html')


@app.route('/files')
def list_files():
    files_with_size = []
    for file in os.listdir('inference_data'):
        file_path = os.path.join('inference_data', file)
        size = os.path.getsize(file_path)
        files_with_size.append({'name': file, 'size': size})
    return jsonify(files_with_size)


@app.route('/download-prediction/<filename>')
def download_prediction(filename):
    """Download the prediction file"""
    try:
        # Make sure the filename is safe to prevent directory traversal attacks
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join('modeling_data', filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return send_file(file_path, as_attachment=True)




@app.route('/run-model', methods=['POST'])
def run_model():
    """Process model parameters from the UI and run the model"""
    data = None
    try:
        data = request.json

        required_params = ['st_date', 'end_date', 'test_date', 'data_universe']
        for param in required_params:
            if param not in data or not data[param]:
                error_msg = f'Missing required parameter: {param}'
                log_model_run('Failed', data, error_message=error_msg)
                return jsonify({'error': error_msg}), 400

        params = json.dumps({
            "st_date": data['st_date'],
            "end_date": data['end_date'],
            "test_date": data['test_date'],
            "data_universe": data['data_universe'],
        })

        from modeling_data.run_model import run_model_with_params
        result = run_model_with_params(params)

        # Calculate prediction file name based on parameters
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        test_date = data['test_date']
        data_universe = data['data_universe']
        date_obj = datetime.strptime(test_date, "%Y-%m")
        pred_date = (date_obj + relativedelta(months=1)).strftime("%Y-%m")
        prediction_file = f"final_predictions{pred_date}_{data_universe}.csv"

        # Check if prediction file exists
        prediction_file_path = os.path.join('modeling_data', prediction_file)
        if os.path.exists(prediction_file_path):
            result['prediction_file'] = prediction_file

        model_results = result.get('metrics', {})
        log_model_run('Success', data, prediction_file=prediction_file, model_results=model_results)

        return jsonify({
            'status': result['status'],
            'message': 'Model run completed',
            'details': result,
            'parameters': data,
            'prediction_file': prediction_file if os.path.exists(prediction_file_path) else None
        })

    except Exception as e:
        log_model_run('Failed', data, error_message=str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/upload-files')
def upload_files():
    return render_template('upload_files.html')


@app.route('/manage-files')
def manage_files():
    return render_template('manage_models.html')

@app.route('/combine-predictions')
def combine_predictions():
    return render_template('combine_predictions.html')

@app.route('/run-combine-predictions', methods=['POST'])
def run_combine_predictions():
    """Process FHA and Conventional files and run combine_predictions.py"""
    try:
        # Check if files are present
        if 'fha_file' not in request.files or 'conventional_file' not in request.files:
            return jsonify({'error': 'Both FHA and Conventional files are required'}), 400

        fha_file = request.files['fha_file']
        conventional_file = request.files['conventional_file']

        if fha_file.filename == '' or conventional_file.filename == '':
            return jsonify({'error': 'Both files must be selected'}), 400

        # Validate file extensions
        if not fha_file.filename.endswith('.csv') or not conventional_file.filename.endswith('.csv'):
            return jsonify({'error': 'Both files must be CSV files'}), 400

        # Create temp ditory if it doesn't exist
        temp_dir = 'temp_combine'
        os.makedirs(temp_dir, exist_ok=True)

        # Save uploaded files
        fha_filename = secure_filename(fha_file.filename)
        conventional_filename = secure_filename(conventional_file.filename)

        fha_path = os.path.join(temp_dir, fha_filename)
        conventional_path = os.path.join(temp_dir, conventional_filename)

        fha_file.save(fha_path)
        conventional_file.save(conventional_path)

        # Extract date from FHA filename (e.g., final_predictions2025-08_fha.csv -> 2025-08)
        date_str = None
        if 'final_predictions' in fha_filename:
            # Split on "final_predictions" and get the part after it
            after_prefix = fha_filename.split('final_predictions')[1]
            # Remove .csv extension
            after_prefix = after_prefix.rsplit('.', 1)[0] if '.' in after_prefix else after_prefix
            # Extract date part (first 7 characters should be YYYY-MM)
            if len(after_prefix) >= 7 and after_prefix[4] == '-':
                date_str = after_prefix[:7]

        if date_str:
            output_filename = f'combined_predictions_{date_str}.xlsx'
        else:
            # Fallback to default name if date pattern not found
            output_filename = 'combined_predictions.xlsx'

        output_path = os.path.join('.', output_filename)

        # Run the combine_predictions.py script
        import subprocess
        import sys
        cmd = [
            sys.executable,
            'combine_predictions.py',
            '--fha', fha_path,
            '--conventional', conventional_path,
            '--output', output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # Clean up temp files
            if os.path.exists(fha_path):
                os.remove(fha_path)
            if os.path.exists(conventional_path):
                os.remove(conventional_path)
            return jsonify({'error': f'Script execution failed: {result.stderr}'}), 500

        # Check if the expected output file exists
        if not os.path.exists(output_path):
            # Try modeling_data directory
            alt_output_path = os.path.join('modeling_data', output_filename)
            if os.path.exists(alt_output_path):
                output_file = alt_output_path
            else:
                return jsonify({'error': f'Output file not found after script execution. Expected: {output_filename}'}), 500
        else:
            output_file = output_path

        # Clean up temp files
        if os.path.exists(fha_path):
            os.remove(fha_path)
        if os.path.exists(conventional_path):
            os.remove(conventional_path)

        # Directly download the file
        return send_file(output_file, as_attachment=True, download_name=os.path.basename(output_file))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-single-file', methods=['POST'])
def upload_single_file():
    """Process a single file upload with validation"""
    try:
        file_mappings = {
            'bsi_file': {'name': 'BSI_CREDITREPORTING.xlsx', 'type': 'excel'},
            'interest_file': {'name': 'Interest Rate Data.xlsx', 'type': 'excel'},
            'mlw_file': {'name': 'MLW_logins.csv', 'type': 'csv'},
            'oneoff_file': {'name': 'one_off_oct23_to_Feb25.csv', 'type': 'csv'},
            'combined_file': {'name': 'Combined_Payoff_Data_with_RefinanceYes.xlsx', 'type': 'excel'},
            'payoff_file': {'name': 'payoff_reason_file', 'type': 'excel'}
        }

        # Files that need to be saved to dual locations
        dual_location_files = ['BSI_CREDITREPORTING.xlsx', 'MLW_logins.csv', 'one_off_oct23_to_Feb25.csv', 'Interest Rate Data.xlsx']

        file_type = request.form.get('file_type')
        if not file_type or file_type not in file_mappings:
            return jsonify({'error': 'Invalid file type specified'}), 400

        file_info = file_mappings[file_type]

        if 'file' not in request.files:
            return jsonify({'error': f'No file uploaded for {file_info["name"]}'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': f'No file selected for {file_info["name"]}'}), 400

        # Validate file type
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        if file_info['type'] == 'excel' and file_ext != 'xlsx':
            return jsonify({'error': f'Invalid file type. Expected Excel file (.xlsx), got .{file_ext}'}), 400
        elif file_info['type'] == 'csv' and file_ext != 'csv':
            return jsonify({'error': f'Invalid file type. Expected CSV file (.csv), got .{file_ext}'}), 400

        # Create required directories if they don't exist
        upload_dir = 'uploaded_files'
        data_prep_input_dir = os.path.join('data_preperation', 'Input')
        inference_data_dir = 'inference_data'

        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(data_prep_input_dir, exist_ok=True)
        os.makedirs(inference_data_dir, exist_ok=True)

        # Use predefined filename or original filename for payoff files
        if file_info['name'] == 'payoff_reason_file':
            if not re.match(r'^PayoffReason\d{4}-\d{2}\.xlsx$', file.filename):
                return jsonify({'error': 'Invalid filename format. Expected PayoffReasonYYYY-MM.xlsx'}), 400
            predefined_filename = secure_filename(file.filename)
        else:
            predefined_filename = file_info['name']

        primary_file_path = os.path.join(upload_dir, predefined_filename)
        file.save(primary_file_path)

        file_size = os.path.getsize(primary_file_path)
        locations = [primary_file_path]

        # Special handling for payoff_file - save only to inference_data
        if file_info['name'] == 'payoff_reason_file':
            # Copy from uploaded_files to inference_data
            inference_path = os.path.join(inference_data_dir, predefined_filename)
            shutil.copy2(primary_file_path, inference_path)
            locations = [inference_path]
        # Special handling for Combined_Payoff_Data_with_RefinanceYes.xlsx - single location only
        elif file_info['name'] == 'Combined_Payoff_Data_with_RefinanceYes.xlsx':
            # Remove from uploaded_files and copy to data_preperation/Input/Payoffs Reasons
            payoffs_reasons_dir = os.path.join(data_prep_input_dir, 'Payoffs Reasons')
            os.makedirs(payoffs_reasons_dir, exist_ok=True)
            payoffs_path = os.path.join(payoffs_reasons_dir, predefined_filename)
            shutil.copy2(primary_file_path, payoffs_path)
            locations = [payoffs_path]
        # Check if this file needs dual storage
        elif file_info['name'] in dual_location_files:
            if file_info['name'] == 'Interest Rate Data.xlsx':
                # Special handling for Interest Rate Data.xlsx
                # Save to inference_data with original name
                inference_path = os.path.join(inference_data_dir, 'Interest Rate Data.xlsx')
                shutil.copy2(primary_file_path, inference_path)
                locations.append(inference_path)

                # Convert Excel to CSV and save to data_preperation/Input
                data_prep_path = os.path.join(data_prep_input_dir, 'Curinos_Interest_Rate_File_2022-2024.csv')
                # Read Excel file and convert to CSV
                df = pd.read_excel(primary_file_path)
                df.to_csv(data_prep_path, index=False)
                locations.append(data_prep_path)
            else:
                # Standard dual storage for other files
                # Copy to data_preperation/Input
                data_prep_path = os.path.join(data_prep_input_dir, predefined_filename)
                shutil.copy2(primary_file_path, data_prep_path)
                locations.append(data_prep_path)

                # Copy to inference_data
                inference_path = os.path.join(inference_data_dir, predefined_filename)
                shutil.copy2(primary_file_path, inference_path)
                locations.append(inference_path)
        
        # Delete the original file from upload_dir after all copying is complete
        if os.path.exists(primary_file_path):
            os.remove(primary_file_path)
            # Update locations to remove the primary file path since it's deleted
            locations = [loc for loc in locations if loc != primary_file_path]

        # Use actual filename for display in success message for payoff files
        display_name = predefined_filename if file_info['name'] == 'payoff_reason_file' else file_info['name']

        return jsonify({
            'status': 'success',
            'message': f'{display_name} uploaded successfully',
            'file': {
                'name': display_name,
                'size': file_size,
                'locations': locations,
                'dual_storage': file_info['name'] in dual_location_files
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files', methods=['GET'])
def list_files_api():
    """List all files from BestModel and modeling_data directories, categorizing by filename prefix"""
    try:
        all_files = []

        # Scan Modeling/BestModel directory for .pkl files
        model_dir = os.path.join('Modeling', 'BestModel')
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        else:
            for filename in os.listdir(model_dir):
                file_path = os.path.join(model_dir, filename)
                if os.path.isfile(file_path) and filename.endswith('.pkl'):
                    file_size = os.path.getsize(file_path)
                    file_stats = os.stat(file_path)

                    all_files.append({
                        'filename': filename,
                        'size': file_size,
                        'created': file_stats.st_ctime,
                        'modified': file_stats.st_mtime,
                        'path': file_path,
                        'category': 'models',
                        'directory': model_dir
                    })

        # Scan modeling_data directory for CSV and Excel files
        modeling_data_dir = 'modeling_data'
        if not os.path.exists(modeling_data_dir):
            os.makedirs(modeling_data_dir, exist_ok=True)
        else:
            for filename in os.listdir(modeling_data_dir):
                file_path = os.path.join(modeling_data_dir, filename)

                # Only include files (not directories) with specific extensions
                if os.path.isfile(file_path):
                    valid_extensions = ['.csv', '.xlsx']
                    if not any(filename.endswith(ext) for ext in valid_extensions):
                        continue

                    # Determine category based on filename prefix
                    category = 'other'
                    if filename.startswith('final_predictions'):
                        category = 'final_predictions'
                    elif filename.startswith('prediction_data'):
                        category = 'prediction_data'
                    elif filename.startswith('training_data'):
                        category = 'training_data'

                    file_size = os.path.getsize(file_path)
                    file_stats = os.stat(file_path)

                    all_files.append({
                        'filename': filename,
                        'size': file_size,
                        'created': file_stats.st_ctime,
                        'modified': file_stats.st_mtime,
                        'path': file_path,
                        'category': category,
                        'directory': modeling_data_dir
                    })

        # Sort by modification time (newest first)
        all_files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({'files': all_files})

    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500


@app.route('/api/files/rename', methods=['POST'])
def rename_file():
    """Rename a file in the managed directories"""
    try:
        data = request.json

        # Validate required parameters
        if not data or 'old_filename' not in data or 'new_filename' not in data or 'directory' not in data:
            return jsonify({'error': 'old_filename, new_filename, and directory are required'}), 400

        old_filename = data['old_filename'].strip()
        new_filename = data['new_filename'].strip()
        directory = data['directory'].strip()

        # Basic validation
        if not old_filename or not new_filename or not directory:
            return jsonify({'error': 'Filenames and directory cannot be empty'}), 400

        # Ensure filenames are safe (prevent directory traversal)
        if '..' in old_filename or '..' in new_filename or '/' in old_filename or '/' in new_filename or '\\' in old_filename or '\\' in new_filename:
            return jsonify({'error': 'Invalid filename. Directory traversal not allowed'}), 400

        # Get file extension from old filename
        file_ext = old_filename.rsplit('.', 1)[1].lower() if '.' in old_filename else ''

        # Ensure new filename has the same extension
        if not new_filename.endswith(f'.{file_ext}'):
            new_filename += f'.{file_ext}'

        # Validate filename format (allow alphanumeric, hyphens, underscores, dots)
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', old_filename) or not re.match(r'^[a-zA-Z0-9._-]+$', new_filename):
            return jsonify({'error': 'Filename contains invalid characters. Only letters, numbers, dots, hyphens, and underscores are allowed'}), 400

        # Validate file extension
        valid_extensions = ['.pkl', '.csv', '.xlsx']
        if not any(old_filename.endswith(ext) for ext in valid_extensions):
            return jsonify({'error': 'Only .pkl, .csv, and .xlsx files can be renamed'}), 400

        # Determine actual directory path
        if directory == os.path.join('Modeling', 'BestModel'):
            target_dir = directory
        else:
            target_dir = directory

        old_file_path = os.path.join(target_dir, old_filename)
        new_file_path = os.path.join(target_dir, new_filename)

        # Check if old file exists
        if not os.path.exists(old_file_path):
            return jsonify({'error': f'File "{old_filename}" does not exist'}), 404

        # Check if old file is actually a file (not a directory)
        if not os.path.isfile(old_file_path):
            return jsonify({'error': f'"{old_filename}" is not a valid file'}), 400

        # Check if new filename already exists
        if os.path.exists(new_file_path):
            return jsonify({'error': f'File "{new_filename}" already exists'}), 409

        # Perform the rename operation
        try:
            os.rename(old_file_path, new_file_path)
        except OSError as e:
            return jsonify({'error': f'Failed to rename file: {str(e)}'}), 500

        # Get file info for response
        file_size = os.path.getsize(new_file_path)
        file_stats = os.stat(new_file_path)

        return jsonify({
            'status': 'success',
            'message': f'File renamed successfully from "{old_filename}" to "{new_filename}"',
            'old_filename': old_filename,
            'new_filename': new_filename,
            'file_info': {
                'filename': new_filename,
                'size': file_size,
                'modified': file_stats.st_mtime,
                'path': new_file_path,
                'directory': directory
            }
        })

    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    """Delete a file from the managed directories"""
    try:
        data = request.json

        # Validate required parameters
        if not data or 'filename' not in data or 'directory' not in data:
            return jsonify({'error': 'Filename and directory are required'}), 400

        filename = data['filename'].strip()
        directory = data['directory'].strip()

        # Basic validation
        if not filename or not directory:
            return jsonify({'error': 'Filename and directory cannot be empty'}), 400

        # Ensure filename is safe (prevent directory traversal)
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename. Directory traversal not allowed'}), 400

        # Validate file extension
        valid_extensions = ['.pkl', '.csv', '.xlsx']
        if not any(filename.endswith(ext) for ext in valid_extensions):
            return jsonify({'error': 'Only .pkl, .csv, and .xlsx files can be deleted'}), 400

        file_path = os.path.join(directory, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': f'File "{filename}" does not exist'}), 404

        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            return jsonify({'error': f'"{filename}" is not a valid file'}), 400

        # Perform the delete operation
        try:
            os.remove(file_path)
        except OSError as e:
            return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

        return jsonify({
            'status': 'success',
            'message': f'File "{filename}" deleted successfully',
            'deleted_filename': filename,
            'directory': directory
        })

    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    app.run(host="0.0.0.0", port=8000, debug=True)
