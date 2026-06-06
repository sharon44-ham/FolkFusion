# FolkFusion

FolkFusion bridges the present with India's timeless folk art traditions. Upload any photo or modern artwork and have it reimagined in one of five authentic Indian folk art styles — preserving cultural heritage through every transformation.

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
- Style transfer powered by **Stable Horde** — a free volunteer GPU network
- Uses Stable Diffusion img2img with folk art style prompts
- No GPU or paid API needed to run

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
HORDE_API_KEY=your_key_here   # optional — anonymous key works, registered key is faster
```

Run:
```bash
python3 app.py
```

Open `http://localhost:5000`

## Get a free Stable Horde key

Register at [stablehorde.net](https://stablehorde.net) for a free account. Registered users get higher queue priority. The anonymous key (`0000000000`) works too but may be slower during peak hours.
