from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import os
import io
import tempfile
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(file):
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    return size

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload an image file.')
        return redirect(url_for('index'))
    
    # Check file size
    if get_file_size(file) > MAX_FILE_SIZE:
        flash('File too large. Maximum size is 16MB.')
        return redirect(url_for('index'))
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # Get original image dimensions
            with Image.open(filepath) as img:
                width, height = img.size
                
            return render_template('resize.html', 
                                 filename=filename, 
                                 original_width=width, 
                                 original_height=height)
        except Exception as e:
            flash('Error processing image. Please try again.')
            os.remove(filepath)  # Clean up
            return redirect(url_for('index'))

@app.route('/resize', methods=['POST'])
def resize_image():
    filename = request.form.get('filename')
    new_width = request.form.get('width', type=int)
    new_height = request.form.get('height', type=int)
    maintain_aspect = request.form.get('maintain_aspect') == 'on'
    
    if not filename or not new_width or not new_height:
        flash('Missing resize parameters')
        return redirect(url_for('index'))
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        flash('File not found')
        return redirect(url_for('index'))
    
    try:
        with Image.open(filepath) as img:
            if maintain_aspect:
                # Calculate aspect ratio preserving dimensions
                img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
                resized_img = img
            else:
                # Resize to exact dimensions
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save resized image to memory
            img_io = io.BytesIO()
            format = img.format if img.format else 'JPEG'
            resized_img.save(img_io, format=format)
            img_io.seek(0)
            
            # Clean up original file
            os.remove(filepath)
            
            # Generate download filename
            name, ext = os.path.splitext(filename)
            download_filename = f"{name}_resized_{new_width}x{new_height}{ext}"
            
            return send_file(
                img_io,
                mimetype=f'image/{format.lower()}',
                as_attachment=True,
                download_name=download_filename
            )
            
    except Exception as e:
        flash('Error resizing image. Please try again.')
        if os.path.exists(filepath):
            os.remove(filepath)  # Clean up
        return redirect(url_for('index'))

# Clean up old files periodically (basic cleanup)
@app.before_request
def cleanup_old_files():
    try:
        now = datetime.now().timestamp()
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                # Remove files older than 1 hour
                if now - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
    except:
        pass  # Ignore cleanup errors

if __name__ == '__main__':
    app.run(debug=True)