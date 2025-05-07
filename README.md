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
Please manually download the ViT-B checkpoint from Meta AI's official repository:
https://github.com/facebookresearch/segment-anything#model-checkpoints
Place the file in the resource/ folder as:
```bash
resource/sam_vit_b_01ec64.pth
```

# Run the App
```bash
python app.py
```

Visit http://127.0.0.1:5000 in your browser.
