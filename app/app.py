import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

annotations = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_grid_position(x, y, width, height):
    cell_width = width / 8
    cell_height = height / 8
    col = int(x // cell_width)
    row = int(y // cell_height)
    return (col, row)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        with Image.open(filepath) as img:
            width, height = img.size
            annotations[filename] = {
                'width': width,
                'height': height,
                'texts': []
            }
        
        return redirect(url_for('editor', filename=filename))
    return redirect(request.url)

@app.route('/editor/<filename>')
def editor(filename):
    return render_template('editor.html', 
                         filename=filename,
                         width=annotations[filename]['width'],
                         height=annotations[filename]['height'])

@app.route('/add_text', methods=['POST'])
def add_text():
    data = request.json
    filename = data['filename']
    x = int(data['x'])
    y = int(data['y'])
    text = data['text']
    action = data.get('action', 'add')
    
    width = annotations[filename]['width']
    height = annotations[filename]['height']
    
    grid_col, grid_row = get_grid_position(x, y, width, height)
    
    # Store annotation with action
    annotations[filename]['texts'].append({
        'text': text,
        'x': x,
        'y': y,
        'grid_position': (grid_col, grid_row),
        'action': action
    })
    
    # Build cumulative AI prompt
    prompt_entries = []
    for item in annotations[filename]['texts']:
        article = 'a' if item['action'] == 'add' else 'the'
        prompt_entries.append(f"{item['action']} {article} {item['text']} at {item['grid_position']}")
    ai_prompt = ", ".join(prompt_entries)
    
    print(f"Generated AI Prompt: {ai_prompt}")
    
    return jsonify(success=True)

@app.route('/remove_text', methods=['POST'])
def remove_text():
    data = request.json
    filename = data['filename']
    text = data['text']
    grid_position = tuple(data['grid_position'])
    
    # Find and remove the annotation
    if filename in annotations:
        annotations_list = annotations[filename]['texts']
        # Remove all matching entries (both add and remove)
        annotations[filename]['texts'] = [
            item for item in annotations_list
            if not (item['text'] == text and item['grid_position'] == grid_position)
        ]
    
    # Rebuild prompt
    prompt_entries = []
    for item in annotations[filename]['texts']:
        article = 'a' if item['action'] == 'add' else 'the'
        prompt_entries.append(f"{item['action']} {article} {item['text']} at {item['grid_position']}")
    ai_prompt = ", ".join(prompt_entries)
    print(f"Updated AI Prompt: {ai_prompt}")
    
    return jsonify(success=True)


@app.route('/get_annotations/<filename>')
def get_annotations(filename):
    return jsonify(annotations.get(filename, {}))

@app.route('/clear_annotations', methods=['POST'])
def clear_annotations():
    data = request.json
    filename = data['filename']
    if filename in annotations:
        annotations[filename]['texts'] = []
        print("Cleared all annotations")
    return jsonify(success=True)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)