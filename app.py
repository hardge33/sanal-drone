from flask import Flask, request, jsonify
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import *
import tempfile
import math

app = Flask(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

def get_coordinates_from_parsel(il, ilce, ada, parsel):
    try:
        url = f"https://parselsorgu.tkgm.gov.tr/api/parsel/{il}/{ilce}/{ada}/{parsel}"
        response = requests.get(url, timeout=10)
        data = response.json()
        lat = data['features'][0]['geometry']['coordinates'][1]
        lon = data['features'][0]['geometry']['coordinates'][0]
        return lat, lon
    except:
        return None, None

def get_satellite_image(lat, lon, zoom=17):
    url = f"https://maps.googleapis.com/maps/api/staticmap"
    params = {
        'center': f'{lat},{lon}',
        'zoom': zoom,
        'size': '640x640',
        'maptype': 'satellite',
        'key': GOOGLE_MAPS_API_KEY
    }
    response = requests.get(url, params=params)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    tmp.write(response.content)
    tmp.close()
    return tmp.name

def create_drone_video(lat, lon, logo_text="İLANDİO"):
    frames = []
    zoom_levels = [13, 14, 15, 16, 17, 17, 17]
    
    for zoom in zoom_levels:
        img_path = get_satellite_image(lat, lon, zoom)
        img = Image.open(img_path).convert('RGB')
        img = img.resize((1080, 1080))
        
        # Logo ekle
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 980, 1080, 1080], fill=(0,0,0,180))
        draw.text((50, 995), logo_text, fill='white')
        
        frames.append(np.array(img))
        os.unlink(img_path)
    
    # Video oluştur
    clips = []
    for frame in frames:
        clip = ImageClip(frame).set_duration(0.8)
        clips.append(clip)
    
    final = concatenate_videoclips(clips, method='compose')
    
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
    final.write_videofile(output_path, fps=24, codec='libx264', audio=False)
    
    return output_path

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    il = data.get('il')
    ilce = data.get('ilce')
    ada = data.get('ada')
    parsel = data.get('parsel')
    logo = data.get('logo', 'İLANDİO')
    
    lat, lon = get_coordinates_from_parsel(il, ilce, ada, parsel)
    
    if not lat:
        return jsonify({'error': 'Parsel bulunamadı'}), 404
    
    video_path = create_drone_video(lat, lon, logo)
    
    with open(video_path, 'rb') as f:
        video_data = f.read()
    
    os.unlink(video_path)
    
    return jsonify({
        'success': True,
        'video_base64': video_data.hex()
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
