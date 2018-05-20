from flask import Flask, jsonify

apiserver = Flask(__name__)

emulator =  {
                'status'    : u'RUNNING',
                'uptime'    : u'1min',
                'version'   : u'1.0beta'
            }

@apiserver.route("/functions-emulator/v1/emulator", methods=['GET'])
def get_emulator():
    return jsonify({'emulator': emulator})

if __name__ == "__main__":
    apiserver.run()
