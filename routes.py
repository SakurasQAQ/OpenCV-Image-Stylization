import os
from flask import Blueprint, request, render_template, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
from sam_func import SAMSegmentor
from PIL import Image
from stylize_back import cartoon_effect
from stylize_front import cartoonize_foreground
import cv2

from animegan2_front import AnimeGANv2Front
from animegan2_back import AnimeGANv2Back 


animegan_front = AnimeGANv2Front("checkpoints/AnimeGANv2_best.pth")
animegan_back = AnimeGANv2Back("checkpoints/AnimeGANv2_best.pth")

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


    def scale_point(pt, orig_w, orig_h, tgt_w, tgt_h):
        x = int(pt[0] * tgt_w / orig_w)
        y = int(pt[1] * tgt_h / orig_h)
        return [x, y]


    orig_w = orig_size.get("width") if orig_size else 1024
    orig_h = orig_size.get("height") if orig_size else 1024
    tgt_w, tgt_h = 1024, 1024


    fg = [scale_point([pt["x"], pt["y"]], orig_w, orig_h, tgt_w, tgt_h) for pt in fg_dict]
    bg = [scale_point([pt["x"], pt["y"]], orig_w, orig_h, tgt_w, tgt_h) for pt in bg_dict]
    points = fg + bg
    labels = [1] * len(fg) + [0] * len(bg)


    box_np = None
    if box_dict and len(box_dict) == 2:
        x0, y0 = scale_point([box_dict[0]["x"], box_dict[0]["y"]], orig_w, orig_h, tgt_w, tgt_h)
        x1, y1 = scale_point([box_dict[1]["x"], box_dict[1]["y"]], orig_w, orig_h, tgt_w, tgt_h)
        box_np = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]

    segmentor.load_image(image_path)


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
    fg_result = data.get("selected_foreground")
    bg_result = data.get("selected_background")
    filename = data.get("filename")

    if not fg_result or not bg_result or not filename:
        return jsonify({"message": "Missing required data"}), 400

    print(f"User confirmed: {fg_result} (foreground), {bg_result} (background) for {filename}")
    return jsonify({"message": f"Confirmed foreground: {os.path.basename(fg_result)}, background: {os.path.basename(bg_result)}"})




@app_bp.route('/stylize', methods=['POST'])
def stylize():
    data = request.get_json()
    mask_path = data.get("mask_path")
    filename  = data.get("filename")
    stylePart = data.get("stylePart", "foreground")  
    style = data.get("style", "Hayao")      

    if not filename or not mask_path:
        return jsonify({"message": "Missing filename or mask_path"}), 400

    img_path = os.path.join("static/uploads", filename)
    img = cv2.imread(img_path)
    mask = cv2.imread(mask_path, 0)

    if img is None or mask is None:
        return jsonify({"message": "Image or mask not found"}), 404


    if style == "Hayao":
        if stylePart == "foreground":
            styled = cartoonize_foreground(img, mask,style="Hayao")
        else:
            styled = cartoon_effect(img, mask,style="Hayao")

    elif style == "Shinkai":
        if stylePart == "foreground":
            styled = cartoonize_foreground(img, mask,style="Shinkai")
        else:
            styled = cartoon_effect(img, mask,style="Shinkai")
        
    elif style == "Hosoda":
        if stylePart == "foreground":
            styled = cartoonize_foreground(img, mask,style="Hosoda")
        else:
            styled = cartoon_effect(img, mask,style="Hosoda")
            
    elif style == "Paprika":
        if stylePart == "foreground":
            styled = cartoonize_foreground(img, mask,style="Paprika")
        else:
            styled = cartoon_effect(img, mask,style="Paprika")
    else:
        if stylePart == "foreground":
            styled = animegan_front.stylize_foreground(img, mask)
        else:
            styled = animegan_back.stylize_background(img, mask)

    
    # else:
    #     if stylePart == "foreground":
    #         styled = cartoonize_foreground(img, mask)
    #     else:
    #         styled = cartoon_effect(img, mask)

    out_name = f"stylized_{style}_{stylePart}_{os.path.splitext(filename)[0]}.jpg"
    out_path = os.path.join("static/results", out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, styled)

    return jsonify({"message": "OK", "styled_path": out_path})