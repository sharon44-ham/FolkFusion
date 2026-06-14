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
from gradio_client import Client, handle_file

load_dotenv()

app = Flask(__name__)
app.secret_key = 'folkfusion-secret'

UPLOAD_FOLDER = Path('static/uploads')
CONVERTED_FOLDER = Path('static/converted')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Stable Horde — free volunteer GPU network, no account needed
HORDE_API = "https://stablehorde.net/api/v2"
HORDE_KEY = os.environ.get("HORDE_API_KEY", "0000000000")  # anonymous key works

# ── Inference parameters ──────────────────────────────────────────────────────
# image_guidance_scale: lower = more stylistic change, higher = more original preserved
# guidance_scale: higher = stronger adherence to the style prompt
# num_inference_steps: more = better quality (costs time on Colab T4)
INFERENCE_CONFIG = {
    'strength': 0.65,       # how much to transform (0=no change, 1=ignore original completely)
    'guidance_scale': 12.0, # how strongly to follow the style prompt
    'num_inference_steps': 40,
}

STYLES = {
    'warli': {
        'label': 'Warli',
        'desc': 'Maharashtra tribal art',
        'origin': 'Maharashtra, India',
        'prompt': (
            'Transform into Warli tribal folk painting from Maharashtra India. '
            'Minimalist white geometric stick figures — circles for heads, triangles '
            'for torsos — arranged in ritual dance and harvest scenes. '
            'Dark terracotta mud-brown background. '
            'No shading, no gradients, pure flat two-tone composition, '
            'handpainted on mud wall texture, sacred tribal aesthetic.'
        ),
    },
    'madhubani': {
        'label': 'Madhubani',
        'desc': 'Bihar folk painting',
        'origin': 'Mithila, Bihar, India',
        'prompt': (
            'Transform into Madhubani Mithila folk painting from Bihar India. '
            'Bold black ink outlines filled with vivid flat colors — crimson, saffron, '
            'emerald, indigo, golden yellow. '
            'Symmetrical composition with intricate fish, lotus, peacock and elephant motifs. '
            'Double-line black borders, no empty space, every gap filled with fine '
            'crosshatch or dot patterns, handpainted on handmade paper.'
        ),
    },
    'pattachitra': {
        'label': 'Pattachitra',
        'desc': 'Odisha scroll painting',
        'origin': 'Odisha, India',
        'prompt': (
            'Transform into Odisha Pattachitra folk painting. '
            'Fine black pen outlines, flat natural pigments in deep red, golden yellow, '
            'black and white. '
            'Decorative floral and creeper scroll border framing the entire image. '
            'Traditional mythological figures with elongated eyes and stylized gestures. '
            'No perspective or shadow, every detail outlined in black, '
            'rich textile-like surface, traditional scroll painting style.'
        ),
    },
    'gond': {
        'label': 'Gond',
        'desc': 'Madhya Pradesh tribal art',
        'origin': 'Madhya Pradesh, India',
        'prompt': (
            'Transform into Gond tribal art from Madhya Pradesh India. '
            'Every shape filled with dense repetitive patterns of tiny dots, dashes '
            'and parallel lines creating texture and movement. '
            'Bold earthy palette — cadmium red, canary yellow, cobalt blue, forest green '
            'on black background. '
            'Animals, trees and figures dissolved into intricate mark-making, '
            'flat graphic style, no shading or photographic realism.'
        ),
    },
    'kalamkari': {
        'label': 'Kalamkari',
        'desc': 'Andhra Pradesh pen art',
        'origin': 'Andhra Pradesh, India',
        'prompt': (
            'Transform into Srikalahasti Kalamkari pen art from Andhra Pradesh India. '
            'Hand-drawn flowing black outlines, flat vegetable dye fills in indigo blue, '
            'brick red, mustard yellow, forest green and black. '
            'Narrative mythological figures with elaborate headdresses and jewellery. '
            'Fine floral vine borders, no photographic realism, '
            'fully hand-illustrated folk art look.'
        ),
    },
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def run_via_colab(src_path: Path, style: str, out_path: Path) -> Path:
    colab_url = os.environ.get('COLAB_URL')
    client = Client(colab_url)
    result = client.predict(
        image=handle_file(str(src_path)),
        prompt=STYLES[style]['prompt'],
        strength=INFERENCE_CONFIG['strength'],
        guidance=INFERENCE_CONFIG['guidance_scale'],
        steps=INFERENCE_CONFIG['num_inference_steps'],
        api_name="/predict",
    )
    Image.open(result).save(out_path)
    return out_path


def run_via_horde(src_path: Path, style: str, out_path: Path) -> Path:
    img = Image.open(src_path).convert('RGB')
    img.thumbnail((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='WEBP')
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    headers = {"apikey": HORDE_KEY, "Content-Type": "application/json"}
    payload = {
        "prompt": STYLES[style]['prompt'],
        "params": {
            "steps": INFERENCE_CONFIG['num_inference_steps'],
            "cfg_scale": INFERENCE_CONFIG['guidance_scale'],
            "denoising_strength": INFERENCE_CONFIG['strength'],
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

    for _ in range(80):
        time.sleep(3)
        if requests.get(f"{HORDE_API}/generate/check/{job_id}",
                        headers=headers, timeout=10).json().get('done'):
            break

    result = requests.get(f"{HORDE_API}/generate/status/{job_id}",
                          headers=headers, timeout=15)
    generations = result.json().get('generations', [])
    if not generations:
        raise Exception("Stable Horde returned no image. Try again.")

    out_path.write_bytes(base64.b64decode(generations[0]['img']))
    return out_path


def run_style_transfer(src_path: Path, style: str) -> Path:
    out_path = CONVERTED_FOLDER / f"{src_path.stem}_{style}.png"
    if out_path.exists():
        return out_path

    if os.environ.get('COLAB_URL'):
        return run_via_colab(src_path, style, out_path)
    return run_via_horde(src_path, style, out_path)


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
