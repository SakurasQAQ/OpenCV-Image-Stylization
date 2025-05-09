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
    box_dict = data.get('box', None)
    filename = data.get('filename', None)
    orig_size = data.get('original_size', None)

    if not filename:
        return jsonify({"message": "filename parameters missing"}), 400

    image_path = os.path.join('static/uploads', filename)
    if not os.path.exists(image_path):
        return jsonify({"message": f"Image file not found: {filename}"}), 404

    # 坐标缩放函数
    def scale_point(pt, orig_w, orig_h, tgt_w, tgt_h):
        x = int(pt[0] * tgt_w / orig_w)
        y = int(pt[1] * tgt_h / orig_h)
        return [x, y]

    # 原始尺寸
    orig_w = orig_size.get("width") if orig_size else 1024
    orig_h = orig_size.get("height") if orig_size else 1024
    tgt_w, tgt_h = 1024, 1024

    # 点坐标缩放
    fg = [scale_point([pt["x"], pt["y"]], orig_w, orig_h, tgt_w, tgt_h) for pt in fg_dict]
    bg = [scale_point([pt["x"], pt["y"]], orig_w, orig_h, tgt_w, tgt_h) for pt in bg_dict]
    points = fg + bg
    labels = [1] * len(fg) + [0] * len(bg)

    # 框坐标缩放
    box_np = None
    if box_dict and len(box_dict) == 2:
        x0, y0 = scale_point([box_dict[0]["x"], box_dict[0]["y"]], orig_w, orig_h, tgt_w, tgt_h)
        x1, y1 = scale_point([box_dict[1]["x"], box_dict[1]["y"]], orig_w, orig_h, tgt_w, tgt_h)
        box_np = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]

    segmentor.load_image(image_path)

    # 调用组合接口
    if box_np:
        masks, scores = segmentor.segment_with_box_and_points(box=box_np, points=points, labels=labels)
        mode_used = "box+point" if points else "box-only"
    else:
        masks, scores = segmentor.segment_all_masks(points, labels)
        mode_used = "point-only"

    name_without_ext = os.path.splitext(filename)[0]
    saved_paths = segmentor.export_multiple_masks(
        masks,
        base_path="static/uploads",
        prefix=f"result_{name_without_ext}"
    )

    return jsonify({
        "message": f"Segmentation completed using [{mode_used}], {len(saved_paths)} results generated.",
        "result": saved_paths,
        "mode": mode_used
    })



@app_bp.route('/confirm_result', methods=['POST'])
def confirm_result():
    data = request.get_json()
    selected_result = data.get("selected_result")
    filename = data.get("filename")

    if not selected_result or not filename:
        return jsonify({"message": "Missing required data"}), 400

    print(f"User confirmed: {selected_result} for {filename}")
    return jsonify({"message": f"Selected result received: {os.path.basename(selected_result)}"})
