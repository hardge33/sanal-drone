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
    try:
        if request.content_type and 'multipart' in request.content_type:
            logo = request.form.get('logo', 'ILANDIO')
            alt_yazi = request.form.get('alt_yazi', '')
            if 'image' not in request.files:
                return jsonify({'error': 'Gorsel bulunamadi - form', 'fields': list(request.form.keys()), 'files': list(request.files.keys())}), 200
            image_file = request.files['image']
            img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            image_file.save(img_tmp.name)
            size = os.path.getsize(img_tmp.name)
            if size < 100:
                return jsonify({'error': 'Dosya bos', 'size': size}), 200
        else:
            data = request.get_json(force=True)
            logo = data.get('logo', 'ILANDIO')
            alt_yazi = data.get('alt_yazi', '')
            image_base64 = data.get('image', '')
            if len(image_base64) < 10:
                return jsonify({'error': 'image bos', 'len': len(image_base64), 'keys': list(data.keys())}), 200
            img_data = image_base64.split(',')[-1] if ',' in image_base64 else image_base64
            try:
                decoded = base64.b64decode(img_data)
            except Exception as e:
                return jsonify({'error': 'base64 decode hatasi', 'detail': str(e), 'ilk100': img_data[:100]}), 200
            if len(decoded) < 100:
                return jsonify({'error': 'decoded cok kucuk', 'size': len(decoded)}), 200
            img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img_tmp.write(decoded)
            img_tmp.close()
            size = os.path.getsize(img_tmp.name)
            if size < 100:
                return jsonify({'error': 'Kaydedilen dosya bos', 'size': size}), 200

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name

        vf = (
            "scale=1080:1080,"
            "zoompan=z='min(zoom+0.002,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=75:s=1080x1080,"
            "fade=t=in:st=0:d=1,"
            "drawtext=text='{}':fontcolor=white:fontsize=48:x=50:y=H-100:box=1:boxcolor=black@0.5:boxborderw=10,"
            "drawtext=text='{}':fontcolor=white:fontsize=28:x=50:y=H-50:box=1:boxcolor=black@0.5:boxborderw=8"
        ).format(logo, alt_yazi)

        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', img_tmp.name,
            '-vf', vf,
            '-t', '5',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            output_path
        ]

        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        with open(output_path, 'rb') as f:
            video_base64 = base64.b64encode(f.read()).decode()
        os.unlink(img_tmp.name)
        os.unlink(output_path)
        return jsonify({'success': True, 'video': video_base64})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Video uretilemedi', 'detail': e.stderr.decode()}), 200
    except Exception as e:
        return jsonify({'error': 'Genel hata', 'detail': str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
