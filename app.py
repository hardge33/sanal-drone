from flask import Flask, request, jsonify
import os
import base64
import tempfile
import subprocess

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    image_base64 = data.get('image')
    logo = data.get('logo', 'ILANDIO')
    alt_yazi = data.get('alt_yazi', '')

    if not image_base64:
        return jsonify({'error': 'Gorsel bulunamadi'}), 400

    img_data = image_base64
    if ',' in img_data:
        img_data = img_data.split(',')[1]

    img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img_tmp.write(base64.b64decode(img_data))
    img_tmp.close()

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name

    vf = (
        "scale=1080:1080,"
        "zoompan=z='min(zoom+0.002,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1080x1080,"
        "fade=t=in:st=0:d=1,"
        "drawtext=text='{}':fontcolor=white:fontsize=48:x=50:y=H-100:box=1:boxcolor=black@0.5:boxborderw=10,"
        "drawtext=text='{}':fontcolor=white:fontsize=28:x=50:y=H-50:box=1:boxcolor=black@0.5:boxborderw=8"
    ).format(logo, alt_yazi)

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', img_tmp.name,
        '-vf', vf,
        '-t', '8',
        '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264',
        output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        with open(output_path, 'rb') as f:
            video_base64 = base64.b64encode(f.read()).decode()
        os.unlink(img_tmp.name)
        os.unlink(output_path)
        return jsonify({'success': True, 'video': video_base64})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Video uretilemedi', 'detail': e.stderr.decode()}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
