import os
import io
import uuid
import base64
import time
import requests
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'folkfusion-secret'

UPLOAD_FOLDER = Path('static/uploads')
CONVERTED_FOLDER = Path('static/converted')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Stable Horde — free volunteer GPU network, no account needed
HORDE_API = "https://stablehorde.net/api/v2"
HORDE_KEY = os.environ.get("HORDE_API_KEY", "0000000000")  # anonymous key works

STYLES = {
    'warli': {
        'label': 'Warli',
        'desc': 'Maharashtra tribal art',
        'origin': 'Maharashtra, India',
        'prompt': (
            'Transform this into Warli tribal folk art from Maharashtra, India. '
            'White geometric stick figures, circles, triangles and squares on a dark '
            'terracotta brown background. Minimal, sacred, handpainted tribal style.'
        ),
    },
    'madhubani': {
        'label': 'Madhubani',
        'desc': 'Bihar folk painting',
        'origin': 'Mithila, Bihar, India',
        'prompt': (
            'Transform this into a Madhubani folk painting from Mithila, Bihar, India. '
            'Vibrant saturated colors, bold black outlines, intricate floral and animal '
            'motifs, fish and peacock patterns, traditional handpainted style.'
        ),
    },
    'pattachitra': {
        'label': 'Pattachitra',
        'desc': 'Odisha scroll painting',
        'origin': 'Odisha, India',
        'prompt': (
            'Transform this into a Pattachitra painting from Odisha, India. '
            'Rich red, yellow and black palette, intricate fine-line details, '
            'mythological figures, floral borders, traditional scroll painting style.'
        ),
    },
    'gond': {
        'label': 'Gond',
        'desc': 'Madhya Pradesh tribal art',
        'origin': 'Madhya Pradesh, India',
        'prompt': (
            'Transform this into Gond tribal art from Madhya Pradesh, India. '
            'Intricate dot and dash patterns filling every shape, bright earthy colors, '
            'animals and nature rendered in dense repetitive marks, folk painting style.'
        ),
    },
    'kalamkari': {
        'label': 'Kalamkari',
        'desc': 'Andhra Pradesh pen art',
        'origin': 'Andhra Pradesh, India',
        'prompt': (
            'Transform this into Kalamkari art from Andhra Pradesh, India. '
            'Hand-drawn pen and vegetable dye style, earthy indigo, red and black tones, '
            'mythological narrative figures, flowing lines and nature motifs.'
        ),
    },
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def run_style_transfer(src_path: Path, style: str) -> Path:
    style_info = STYLES[style]
    stem = src_path.stem
    out_path = CONVERTED_FOLDER / f"{stem}_{style}.png"

    if out_path.exists():
        return out_path

    # Resize to 512x512 max (Stable Horde requirement)
    img = Image.open(src_path).convert('RGB')
    img.thumbnail((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='WEBP')
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    headers = {"apikey": HORDE_KEY, "Content-Type": "application/json"}

    payload = {
        "prompt": style_info['prompt'],
        "params": {
            "steps": 30,
            "cfg_scale": 10,
            "denoising_strength": 0.5,
            "width": 512,
            "height": 512,
            "sampler_name": "k_euler_a",
        },
        "source_image": img_b64,
        "source_processing": "img2img",
        "r2": False,
        "nsfw": False,
    }

    resp = requests.post(f"{HORDE_API}/generate/async", json=payload,
                         headers=headers, timeout=30)
    resp.raise_for_status()
    job_id = resp.json()['id']

    # Poll until done (max ~4 minutes)
    for _ in range(80):
        time.sleep(3)
        check = requests.get(f"{HORDE_API}/generate/check/{job_id}",
                             headers=headers, timeout=10)
        if check.json().get('done'):
            break

    result = requests.get(f"{HORDE_API}/generate/status/{job_id}",
                          headers=headers, timeout=15)
    generations = result.json().get('generations', [])
    if not generations:
        raise Exception("Stable Horde returned no image. Try again.")

    img_data = base64.b64decode(generations[0]['img'])
    out_path.write_bytes(img_data)
    return out_path


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('image')
    if not file or file.filename == '':
        flash('Please select an image.')
        return redirect(url_for('index'))
    if not allowed_file(file.filename):
        flash('Unsupported file type. Use PNG, JPG, or WEBP.')
        return redirect(url_for('index'))

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(UPLOAD_FOLDER / filename)
    return redirect(url_for('show', filename=filename))


@app.route('/show/<filename>')
def show(filename):
    return render_template('show.html', filename=filename, styles=STYLES)


@app.route('/convert/<filename>/<style>')
def convert(filename, style):
    if style not in STYLES:
        flash('Unknown style.')
        return redirect(url_for('show', filename=filename))
    return render_template('loading.html', filename=filename, style=style,
                           style_label=STYLES[style]['label'])


@app.route('/process/<filename>/<style>', methods=['POST'])
def process(filename, style):
    if style not in STYLES:
        return jsonify({'error': 'Unknown style'}), 400

    src_path = UPLOAD_FOLDER / filename
    if not src_path.exists():
        return jsonify({'error': 'Original image not found'}), 404

    try:
        out_path = run_style_transfer(src_path, style)
        return jsonify({'result': url_for('result', filename=filename, style=style)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/result/<filename>/<style>')
def result(filename, style):
    stem = Path(filename).stem
    converted = f"{stem}_{style}.png"
    return render_template(
        'result.html',
        original=filename,
        converted=converted,
        style=STYLES[style]['label'],
        styles=STYLES,
        current_style=style,
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
