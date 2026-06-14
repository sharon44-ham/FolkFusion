# FolkFusion

FolkFusion bridges the present with India's timeless folk art traditions. Upload any artwork or image and have it reimagined in one of five authentic Indian folk art styles — preserving cultural heritage through every transformation.

## What it does

Upload an image → choose a traditional art form → get back your image reinterpreted in that style, with the original content preserved.

## Supported styles

| Style | Origin |
|---|---|
| **Warli** | Maharashtra — white geometric tribal figures on terracotta |
| **Madhubani** | Mithila, Bihar — vibrant colors, bold outlines, floral motifs |
| **Pattachitra** | Odisha — rich reds and yellows, mythological figures, scroll borders |
| **Gond** | Madhya Pradesh — dense dot and line patterns filling every shape |
| **Kalamkari** | Andhra Pradesh — hand-drawn pen art, earthy indigo and red tones |

## How it works

- Built with **Flask** (Python)
- Two backends supported:
  - **Google Colab** (recommended) — runs Stable Diffusion img2img on a free T4 GPU, exposed via Gradio
  - **Stable Horde** (fallback) — free volunteer GPU network, no setup needed
- If `COLAB_URL` is set in `.env`, Colab is used. Otherwise falls back to Stable Horde automatically.

## Setup

```bash
git clone https://github.com/sharon44-ham/folkfusion.git
cd folkfusion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```
HORDE_API_KEY=0000000000
COLAB_URL=                   # paste your gradio.live URL here when using Colab
```

Run:
```bash
python3 app.py
```

Open `http://localhost:5000`

## Using the Colab backend (better results)

1. Upload `colab_server.ipynb` to [Google Colab](https://colab.research.google.com)
2. Set runtime to **T4 GPU** (Runtime → Change runtime type)
3. Run Cell 1 (~2 min to install deps), then Cell 2 (~3 min to load `runwayml/stable-diffusion-v1-5`)
4. Copy the `gradio.live` URL printed at the end
5. Paste it into `.env` as `COLAB_URL=https://xxxx.gradio.live`
6. Restart Flask

## Using the Stable Horde fallback

No setup needed. The anonymous key (`0000000000`) works out of the box. Register at [stablehorde.net](https://stablehorde.net) for a free account to get higher queue priority.
