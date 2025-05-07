from flask import Flask
from routes import app_bp
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#create menu        
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  

app.register_blueprint(app_bp)

if __name__ == '__main__':
    print("SUCCESSFUL! App running at http://127.0.0.1:5000")
    app.run(debug=True)