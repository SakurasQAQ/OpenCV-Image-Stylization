# img_flask
OpenCV image opreation project

# how to run this project? 
## (optional)Set up Python environment

```bash
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
```

# Install dependencies
```bash
pip install -r requirements.txt
```

# Model Checkpoint
When the fisrt run the project, the program will automatically download the required weight model'

For CartoonGAN per-trainning model, please follow https://github.com/maciej3031/comixify.git to download pretrained model
comixify/CartoonGAN/pretrained_model and save it in CartoonTest foldier.

# Run the App
```bash
python app.py
```

Visit http://127.0.0.1:5000 in your browser.
