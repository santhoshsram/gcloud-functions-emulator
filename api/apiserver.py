from flask import Flask

apiserver = Flask(__name__)

@apiserver.route("/")
def getHello():
    return "Hello, world!"

if __name__ == "__main__":
    apiserver.run()
