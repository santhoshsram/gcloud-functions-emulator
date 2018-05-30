from flask import Flask, jsonify
import re
import subprocess as sp

apiserver = Flask(__name__)

def get_emulator_info_json():
    emulator = {}

    output = sp.check_output(['functions', 'status'])

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

    return jsonify(emulator)

@apiserver.route("/functions-emulator/v1/emulator", methods=['GET'])
def get_emulator():
    return get_emulator_info_json()

if __name__ == "__main__":
    apiserver.run()
