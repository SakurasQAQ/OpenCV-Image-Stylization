import os
from flask import Blueprint, request, render_template, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
from sam_func import SAMSegmentor
from PIL import Image

# function_ upload Images
app_bp = Blueprint('app', __name__)

segmentor = SAMSegmentor()  

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    image_url = None
    width = height = None

    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            image = Image.open(save_path)
            width, height = image.size 

            image_url = url_for('static', filename='uploads/' + filename)

    return render_template('index.html', image_url=image_url, width=width, height=height)




@app_bp.route('/getpoints', methods=['POST'])
def getpoints():
    data = request.get_json()
    fg_dict = data.get('foreground', [])
    bg_dict = data.get('background', [])
    filename = data.get('filename', None)

    if not filename:
        return jsonify({"message": "缺少 filename 参数"}), 400

    image_path = os.path.join('static/uploads', filename)
    if not os.path.exists(image_path):
        return jsonify({"message": f"找不到图像文件：{filename}"}), 404

    fg = [[pt["x"], pt["y"]] for pt in fg_dict]
    bg = [[pt["x"], pt["y"]] for pt in bg_dict]
    points = fg + bg
    labels = [1] * len(fg) + [0] * len(bg)

    segmentor.load_image(image_path)
    masks, scores = segmentor.segment_all_masks(points, labels)


    name_without_ext = os.path.splitext(filename)[0]
    saved_paths = segmentor.export_multiple_masks(
        masks,
        base_path="static/uploads",
        prefix=f"result_{name_without_ext}"
    )

    return jsonify({
        "message": "Segmentation completed, generating %d candidate results" % len(saved_paths),
        "result": saved_paths,
        "points_used": {
            "foreground": fg,
            "background": bg
        }
    })
