from flask import Flask, jsonify, make_response, request, abort, json
import re
import subprocess
import logging
import base64
import time
import os
import requests

SRC_BASE = '/tmp/cloud-functions'
FUNCTION_FILE_NAME = 'index.js'
EMULATOR_FUNCTIONS_URL = 'http://localhost:8008/v1/projects/cloud-functions/locations/us-central1/functions'

apiserver = Flask(__name__)
apiserver.config['SRC_BASE'] = SRC_BASE
apiserver.config['FUNCTION_FILE_NAME'] = FUNCTION_FILE_NAME
apiserver.config['EMULATOR_FUNCTIONS_URL'] = EMULATOR_FUNCTIONS_URL

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger('gunicorn.error')
    apiserver.logger.handlers = gunicorn_logger.handlers
    apiserver.logger.setLevel(gunicorn_logger.level)

def get_emulator_info_json():
    emulator = {}

    try:
        output = subprocess.check_output(['functions', 'status'])
    except Exception as err:
        apiserver.logger.error("Failed to get emulator status. Error: " + str(err))
        abort(500)


    # Get the status
    match_obj = re.search(r'Status.*\s(\w+)\s.*', output)
    if not match_obj:
        emulator['status'] = 'UNKNOWN'
    else:
        emulator['status'] = match_obj.group(1)

    # Get uptime
    match_obj = re.search(r'Uptime.*\s(\d+\s[\w\(\)]+)\s.*', output)
    if not match_obj:
        emulator['uptime'] = 'UNKNOWN'
    else:
        emulator['uptime'] = match_obj.group(1)

    # Get version
    match_obj = re.search(r'Emulator Version.*\s([\d\.\w-]+)\s.*', output)
    if not match_obj:
        emulator['version'] = 'UNKNOWN'
    else:
        emulator['version'] = match_obj.group(1)

    return emulator


##
## API handler for /functions-emulator/v1/emulator
## Supported Methods: GET
## Description: Returns the current status of the emulator
##
@apiserver.route("/functions-emulator/v1/emulator", methods=['GET'])
def emulator_get():
    return jsonify(get_emulator_info_json())

##
## write_function_source(func_b64enc):
##
## Description: Base64Decodes the functions source and saves it to a
##              file. Helper for functions_post [POST]
## Input Argument: Base64Encoded string of the function source
## Returns:
##      - Non-empty string containing base path where the function
##        source is created, if successfull
##      - Empty string if error writing the source file
##
def write_function_source(func_b64enc):
    timestamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    try:
        func_src = base64.b64decode(func_b64enc)
    except TypeError:
        apiserver.logger.error("Incorrect base64 encoding of function source")
        return ""

    src_dir = os.path.join(apiserver.config['SRC_BASE'], "func-" + timestamp)
    file_path = os.path.join(src_dir, apiserver.config['FUNCTION_FILE_NAME'])

    # Create the source directory and write the file
    try:
        os.makedirs(src_dir)
        func_file = open(file_path, "w")
        func_file.write(func_src)
        func_file.close()
    except Exception as err:
        apiserver.logger.error("Failed to write function source file. Error: " + str(err))
        abort(500)

    return src_dir


##
## build_func_create_cmd
##
## Description: Builds the command to deploy the function. Helper
##              for functions_post [POST]
## Input Argument:
##      JSON (dict) of the following format
##          {
##              "function-name": <STRING>,
##              "entry-point": <STRING>,
##              "trigger-http": <true/false>  # default = true
##              "function-b64enc": <STRING>, # 64 bit encoded function source code
##          }
## Returns:
##      - Non-empty string containing the command if command is built
##        successfully
##      - Empty string if error building the command
##
def build_func_create_cmd(req_json):
    cmd = "functions deploy"

    # Add the function name to the command
    if req_json['function-name']:
        cmd += " " + req_json['function-name']
    else:
        apiserver.logger.error("JSON did not have function name")
        return ""

    # Add the entry point to the command
    if req_json['entry-point']:
        cmd += " --entry-point " + req_json['entry-point']
    else:
        apiserver.logger.warning("JSON did not have entry point")

    # Add the trigger-http flag to the command
    if req_json['trigger-http'] and req_json['trigger-http'].lower() == 'true':
        cmd += " --trigger-http"
    else:
        apiserver.logger.warning("JSON did not have trigger http flag")

    return cmd


##
## deploy_func(src_dir, cmd):
##
## Description: Base64Decodes the functions source and saves it to a
##              file. Helper for functions_post [POST]
## Input Arguments:
##      - src_dir: Source directory where the function source exists
##      - cmd: Command to execute to deploy the function
## Returns:
##      JSON (dict) of the following format
##          {
##              "resource": <resource location>
##          }
##
def deploy_func(src_dir, cmd):
    try:
        exec_cmd = "cd " + src_dir + "; " + cmd
        output = subprocess.check_output(exec_cmd, stderr=subprocess.STDOUT, shell=True)
    except Exception as err:
        apiserver.logger.error("Failed to deploy function. Error: " + str(err))
        abort(500)

    # parse resource from the ouptut
    # resource is the URL where the function can be access over http
    match_obj = re.search(r'Resource.*\s(\w\S+)\s+', output)
    if not match_obj:
        apiserver.logger.error("Unable to extract resource")
        abort(500)

    return {"function-url":match_obj.group(1)}


##
## POST handler for /functions-emulator/v1/functions
##
##  Deploys a new cloud function. Expects a JSON object that
##  represents the cloud function. The expected JSON format is
##      {
##          "function-name": <STRING>,
##          "entry-point": <STRING>,
##          "trigger-http": <true/false>  # default = true
##          "function-b64enc": <STRING>, # 64 bit encoded function source code
##      }
##
@apiserver.route("/functions-emulator/v1/functions", methods=['POST'])
def functions_post():
    if request.json:
        # build the command to deploy the function
        cmd = build_func_create_cmd(request.json)
        if not cmd:
            apiserver.logger.error("Failed to build functions deploy command")
            abort(400)

        # if the function source is present in the request, write it to a file
        if request.json['function-b64enc']:
            src_dir = write_function_source(request.json['function-b64enc'])
            if not src_dir:
                apiserver.logger.error("Failed to write functions source")
                abort(400)
        else:
            apiserver.logger.error("JSON did not have function")
            abort(400)

        # deploy the function
        response_json = deploy_func(src_dir, cmd)
    else:
        apiserver.logger.error("Request does not have JSON")
        abort(400)
    return jsonify(response_json), 201


##
## GET handler for /functions-emulator/v1/functions
##
@apiserver.route("/functions-emulator/v1/functions", methods=['GET'])
def functions_list():
    funcs = []
    resp = requests.get(apiserver.config['EMULATOR_FUNCTIONS_URL'])

    if resp.status_code != 200:
        apiserver.logger.error("Failed to get functions list")
        abort(resp.status_code)

    for f in resp.json()['functions']:
        # Extract just the name from the full path
        func = {}
        match_obj = re.search(r'.*/(\S+)$', f['name'])
        if match_obj:
            func['function-name'] = match_obj.group(1)
        else:
            func['function-name'] = "UNKNOWN"

        # Extract the entry point
        func['entry-point'] = f['entryPoint']

        # Extract the http trigger url if present
        if f['httpsTrigger']['url']:
            func['trigger-http'] = "true"
            func['function-url'] = f['httpsTrigger']['url']
        else:
            func['trigger-http'] = "false"

        # Extract the status
        func['status'] = f['status']

        funcs.append(func)

    return jsonify({'functions': funcs}), 200


##
## GET handler for /functions-emulator/v1/functions/<string:function_name>
##
@apiserver.route("/functions-emulator/v1/functions/<string:function_name>", methods=['GET'])
def functions_get(function_name):
    func = {}
    resp = requests.get(apiserver.config['EMULATOR_FUNCTIONS_URL'] + '/' + function_name)

    if resp.status_code != 200:
        apiserver.logger.error("Failed to get function " + function_name)
        abort(resp.status_code)

    f = resp.json()

    # Extract just the name from the full path
    match_obj = re.search(r'.*/(\S+)$', f['name'])
    if match_obj:
        func['function-name'] = match_obj.group(1)
    else:
        func['function-name'] = "UNKNOWN"

    # Extract the entry point
    func['entry-point'] = f['entryPoint']

    # Extract the http trigger url if present
    if f['httpsTrigger']['url']:
        func['trigger-http'] = "true"
        func['function-url'] = f['httpsTrigger']['url']
    else:
        func['trigger-http'] = "false"

    # Extract the status
    func['status'] = f['status']

    return jsonify(func), 200


##
## DELETE handler for /functions-emulator/v1/functions/<string:function_name>
##
@apiserver.route("/functions-emulator/v1/functions/<string:function_name>", methods=['DELETE'])
def functions_delete(function_name):
    json = {}
    json["function-name"] = function_name

    resp = requests.delete(apiserver.config['EMULATOR_FUNCTIONS_URL'] + '/' + function_name)

    if resp.status_code != 200:
        apiserver.logger.error("Failed to delete function " + function_name)
        json["status"] = "delete failed"
    else:
        json["status"] = "deleted"

    return jsonify(json), resp.status_code


##
## Error Handlers
##
@apiserver.errorhandler(404)
def error_404(error):
    return make_response(jsonify({'error': 'URL Not Found'}), 404)

@apiserver.errorhandler(400)
def error_400(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

@apiserver.errorhandler(500)
def error_404(error):
    return make_response(jsonify({'error': 'Internal Server Error'}), 500)

if __name__ == "__main__":
    apiserver.run()
