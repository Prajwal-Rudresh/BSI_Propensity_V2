import subprocess
import json
import os
import sys
from datetime import datetime


def run_model_with_params(params_json):
    try:
        # Parse parameters
        params = json.loads(params_json)
        files_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python_executable = sys.executable
        run_script_path = os.path.join(files_path, "modeling_data", "run.py")

        # Print the command that's about to be executed
        print(f"\nRunning model with parameters: {params}")
        print(f"\nExecuting command: {python_executable} {run_script_path} '{params_json}'")

        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            [python_executable, run_script_path, params_json],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        # Capture the output for returning later
        stdout_output = ""
        model_results = None

        # Stream output in real-time
        print("\nSubprocess output:\n" + "-"*50)
        for line in process.stdout:
            line = line.rstrip()
            print(line)  # Print in real-time
            stdout_output += line + "\n"

            # Parse MODEL_RESULTS if present
            if line.startswith("MODEL_RESULTS:"):
                try:
                    results_json = line.replace("MODEL_RESULTS:", "").strip()
                    model_results = json.loads(results_json)
                    print(f"\n*** MODEL_RESULTS FOUND AND PARSED ***")
                    print(f"*** Metrics: {model_results} ***\n")
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse MODEL_RESULTS: {e}")

        # Wait for process to complete and get return code
        return_code = process.wait(timeout=1800)  # 30-minute timeout

        # Get any remaining stderr
        stderr_output = process.stderr.read()

        # Check if process was successful
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, [python_executable, run_script_path, params_json], stdout_output, stderr_output)

        print("-"*50)
        print(f"\nCommand completed with return code: {return_code}")

        print(f"\nModel run completed successfully at: {datetime.now().isoformat()}")

        result = {
            'status': 'success',
            'output': stdout_output,
            'execution_time': f"{datetime.now().isoformat()}",
            'completion_message': 'Model run completed successfully and all outputs have been generated.',
            'timestamp': datetime.now().isoformat()
        }

        # Add model results if they were captured
        if model_results:
            result['metrics'] = model_results
            print(f"\n*** ADDING METRICS TO RESULT ***")
            print(f"*** Final result keys: {result.keys()} ***\n")
        else:
            print(f"\n*** WARNING: NO MODEL_RESULTS CAPTURED ***\n")

        return result

    except subprocess.TimeoutExpired as e:
        error_msg = f"Model execution timed out after {e.timeout} seconds. The process may still be running in the background."
        print(f"\nERROR: {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }
    except subprocess.CalledProcessError as e:
        error_msg = f"Script execution failed with return code {e.returncode}"
        print(f"\nERROR: Command failed: {python_executable} {run_script_path} '{params_json}'")
        print(f"Return code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        return {
            'status': 'error',
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"\nERROR: {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # This allows the script to be run directly with parameters
    if len(sys.argv) > 1:
        result = run_model_with_params(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("No parameters provided. Please provide parameters as a JSON string.")
        sys.exit(1)
