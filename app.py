from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for, send_from_directory, g, current_app, send_file
import requests
import os
import socket
import ssl
import sys
import json
import time
import signal
import subprocess
import threading
import psutil
import re
from datetime import datetime
from dotenv import load_dotenv
from jinja2 import ChoiceLoader, FileSystemLoader
import argparse
import logging
import webbrowser
from flask_cors import CORS
import sqlite3
import markdown2
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
from reportlab.lib import colors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"]
    }
})
# Add support for components directory in templates
app.jinja_loader = ChoiceLoader([
    FileSystemLoader('templates'),
    FileSystemLoader('templates/components')
])
app.secret_key = os.urandom(24)  # Required for session management
load_dotenv()

OLLAMA_BASE_URL = "http://localhost:11434"  # Always use HTTP for Ollama

MODEL_SPECS = {
    "deepseek-r1:7b": {
        "ram": "16GB",
        "description": "Balanced performance, suitable for most systems"
    },
    "deepseek-r1:8b": {
        "ram": "24GB",
        "description": "Enhanced capabilities, recommended for mid-range systems"
    },
    "deepseek-r1:14b": {
        "ram": "32GB",
        "description": "Best performance, requires high-end hardware"
    }
}

def check_ollama_status():
    """Check if Ollama service is running and accessible"""
    try:
        logger.info("Checking Ollama service status...")
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            logger.info(f"Ollama service is running. Available models: {[m['name'] for m in models]}")
            return True, None
        else:
            error_msg = f"Ollama service returned status code {response.status_code}"
            logger.error(error_msg)
            return False, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Could not connect to Ollama service. Is it running?"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error checking Ollama status: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def init_app():
    logger.info("Initializing application...")
    ollama_status, error = check_ollama_status()
    if not ollama_status:
        logger.error(f"Ollama service check failed: {error}")
    return app

@app.route('/')
def index():
    logger.info("Accessing landing page...")
    ollama_status, error = check_ollama_status()
    if not ollama_status:
        logger.warning(f"Ollama service not available: {error}")
    # If a model is already selected and initialized, redirect to chat
    if 'model' in session:
        return redirect(url_for('chat'))
    
    try:    
        ollama_running = check_ollama_status()[0]
        logger.info(f"Ollama status: {'running' if ollama_running else 'not running'}")
        
        cert_path = os.path.join(os.path.dirname(__file__), 'ssl', 'cert.pem')
        key_path = os.path.join(os.path.dirname(__file__), 'ssl', 'key.pem')
        logger.info(f"SSL cert exists: {os.path.exists(cert_path)}")
        logger.info(f"SSL key exists: {os.path.exists(key_path)}")
        
        return render_template('landing.html', 
                             models=MODEL_SPECS, 
                             ollama_running=ollama_running)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/chat')
def chat_page():
    # If no model is selected, redirect to model selection
    if 'model' not in session:
        return redirect(url_for('index'))
        
    ollama_running = check_ollama_status()[0]
    return render_template('chat.html',
                         selected_model=session['model'],
                         ollama_running=ollama_running)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        model = data.get('model', session.get('model', 'llama2'))
        chat_id = data.get('chat_id')
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
            
        logger.info(f"Received chat request with model: {model}")
        
        # Check Ollama connection first
        ollama_status, error = check_ollama_status()
        if not ollama_status:
            return jsonify({"error": f"Ollama service not available: {error}"}), 503

        def generate():
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "num_predict": 2048,
                            "temperature": 0.7,
                            "top_k": 40,
                            "top_p": 0.9
                        }
                    },
                    stream=True,
                    timeout=(5, 300)
                )
                
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'Failed to get response from Ollama'})}\n\n"
                    return
                
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            if 'response' in chunk_data:
                                full_response += chunk_data['response']
                                yield f"data: {json.dumps({'response': chunk_data['response']})}\n\n"
                            if chunk_data.get('done', False):
                                # Save the complete response to database
                                conn = get_db()
                                cursor = conn.cursor()
                                timestamp = datetime.now().isoformat()
                                
                                if not chat_id:
                                    cursor.execute(
                                        'INSERT INTO chats (model, prompt, response, timestamp) VALUES (?, ?, ?, ?)',
                                        (model, prompt, full_response, timestamp)
                                    )
                                    conn.commit()
                                    new_chat_id = cursor.lastrowid
                                    yield f"data: {json.dumps({'chat_id': new_chat_id})}\n\n"
                                else:
                                    cursor.execute(
                                        'UPDATE chats SET prompt = ?, response = ? WHERE id = ?',
                                        (prompt, full_response, chat_id)
                                    )
                                    conn.commit()
                        except json.JSONDecodeError:
                            continue
                
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/initialize_model', methods=['POST'])
def initialize_model():
    try:
        data = request.get_json()
        model = data.get('model')
        if not model:
            return jsonify({'error': 'No model specified'}), 400

        logger.info(f"Initializing model: {model}")
        
        # Check Ollama status first
        ollama_status, error = check_ollama_status()
        if not ollama_status:
            return jsonify({'error': f'Ollama service not available: {error}'}), 503

        # Initialize the model
        if initialize_ollama_model(model):
            session['model'] = model
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'error': 'Failed to initialize model'}), 500
    except Exception as e:
        logger.error(f"Error in initialize_model: {str(e)}")
        return jsonify({'error': str(e)}), 500

def format_chunk_with_thinking(chunk):
    """Format the response chunk to identify and mark chain of thought."""
    # Common thinking patterns
    thinking_patterns = [
        (r"Let(?:')?s break this down", "[thinking]Let's break this down"),
        (r"First,? let(?:')?s", "[thinking]First, let's"),
        (r"Let(?:')?s start", "[thinking]Let's start"),
        (r"Let(?:')?s analyze", "[thinking]Let's analyze"),
        (r"Let(?:')?s consider", "[thinking]Let's consider"),
        (r"Let(?:')?s look at", "[thinking]Let's look at"),
        (r"Let(?:')?s examine", "[thinking]Let's examine"),
        (r"Let(?:')?s understand", "[thinking]Let's understand"),
        (r"Let(?:')?s think about", "[thinking]Let's think about"),
        (r"Let(?:')?s approach", "[thinking]Let's approach"),
        (r"Here(?:')?s how", "[thinking]Here's how"),
        (r"We need to", "[thinking]We need to"),
        (r"We should", "[thinking]We should"),
        (r"We can", "[thinking]We can"),
        (r"I(?:')?ll help you", "[thinking]I'll help you"),
        (r"To solve this", "[thinking]To solve this"),
        (r"To address this", "[thinking]To address this"),
        (r"To implement this", "[thinking]To implement this"),
        (r"To create this", "[thinking]To create this"),
        (r"To handle this", "[thinking]To handle this"),
    ]
    
    # Check if this chunk starts a thinking pattern
    for pattern, replacement in thinking_patterns:
        if re.match(pattern, chunk.strip(), re.IGNORECASE):
            # Find the end of the thought (usually ends with a newline)
            parts = chunk.split('\n', 1)
            if len(parts) > 1:
                return f"{replacement}{parts[0][len(pattern):]}\n[/thinking]\n{parts[1]}"
            return f"{replacement}{chunk[len(pattern):]}\n[/thinking]\n"
    
    return chunk

def format_response(response):
    """Format the response to handle special tags and markdown."""
    # Add think tags around chain-of-thought content
    lines = response.split('\n')
    formatted_lines = []
    in_thinking = False
    
    for line in lines:
        # Check for thinking indicators
        thinking_indicators = [
            "Let me think",
            "I'm thinking",
            "Let's see",
            "I'll analyze",
            "Let me analyze",
            "I'll check",
            "Let me check",
            "First,",
            "Second,",
            "Third,",
            "Finally,",
            "Now,",
            "Next,",
            "Then,",
        ]
        
        # If line starts with any thinking indicator, wrap it in think tags
        if any(line.strip().startswith(indicator) for indicator in thinking_indicators):
            if not in_thinking:
                formatted_lines.append("<think>")
                in_thinking = True
            formatted_lines.append(line)
        else:
            if in_thinking:
                formatted_lines.append("</think>")
                in_thinking = False
            formatted_lines.append(line)
    
    # Close any open think tags
    if in_thinking:
        formatted_lines.append("</think>")
    
    return '\n'.join(formatted_lines)

@app.route('/query', methods=['POST'])
def query(model, prompt):
    try:
        # Check Ollama connection first
        ollama_status, error = check_ollama_status()
        if not ollama_status:
            return jsonify({"error": f"Ollama service not available: {error}"}), 503

        def generate():
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "num_predict": 2048,
                            "temperature": 0.7,
                            "top_k": 40,
                            "top_p": 0.9
                        }
                    },
                    stream=True,
                    timeout=(5, 300)
                )
                
                if response.status_code == 200:
                    full_response = ""
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if 'response' in chunk:
                                    chunk_text = format_chunk_with_thinking(chunk['response'])
                                    full_response += chunk_text
                                    yield f"data: {json.dumps({'chunk': chunk_text})}\n\n"
                                
                                if chunk.get('done', False):
                                    try:
                                        save_chat(model, prompt, full_response)
                                    except Exception as e:
                                        logger.error(f"Error saving chat: {str(e)}")
                                    yield f"data: {json.dumps({'done': True})}\n\n"
                                    break
                            except json.JSONDecodeError:
                                continue
                else:
                    error_msg = f"Ollama returned status code {response.status_code}"
                    logger.error(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat_history')
def get_chat_history():
    """Get chat history."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, model, prompt, response, timestamp FROM chats ORDER BY timestamp DESC')
        chats = cur.fetchall()
        
        # Convert to list of dicts for JSON serialization
        chat_list = []
        for chat in chats:
            chat_list.append({
                'id': chat[0],
                'model': chat[1],
                'prompt': chat[2],
                'response': chat[3],
                'timestamp': chat[4]
            })
        
        return jsonify(chat_list)
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return jsonify([])

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear chat history."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('DELETE FROM chats')
        conn.commit()
        logger.info("Chat history cleared successfully")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    try:
        data = request.get_json()
        model = data.get('model', '')
        prompt = data.get('prompt', '')
        response = data.get('response', '')
        
        if not model or not prompt:
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get current timestamp
        timestamp = datetime.now().isoformat()
        
        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chats (model, prompt, response, timestamp) VALUES (?, ?, ?, ?)',
            (model, prompt, response, timestamp)
        )
        conn.commit()
        
        # Get the ID of the newly created chat
        chat_id = cursor.lastrowid
        
        return jsonify({
            'id': chat_id,
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Error saving chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat/<int:chat_id>')
def get_chat(chat_id):
    """Get a specific chat."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT model, prompt, response, timestamp FROM chats WHERE id = ?', (chat_id,))
        chat = cur.fetchone()
        
        if chat is None:
            return jsonify({'error': 'Chat not found'}), 404
            
        return jsonify({
            'model': chat[0],
            'prompt': chat[1],
            'response': chat[2],
            'timestamp': chat[3]
        })
    except Exception as e:
        logger.error(f"Error getting chat {chat_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        
        if chat_id is None:
            return jsonify({'error': 'No chat_id provided'}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export_pdf', methods=['POST'])
@app.route('/export_pdf/<int:chat_id>', methods=['GET'])
def export_pdf(chat_id=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
        from reportlab.lib.units import inch
        import io
        import re
        import markdown2
        import html

        if chat_id is None:
            # Handle POST request with content in body
            data = request.get_json()
            content = data.get('content', '')
            if not content:
                return jsonify({'error': 'No content provided'}), 400
            user_content = ""
            assistant_content = content
        else:
            # Handle GET request with chat_id
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT prompt, response FROM chats WHERE id = ?', (chat_id,))
            chat = cursor.fetchone()
            
            if not chat:
                return jsonify({'error': 'Chat not found'}), 404
                
            user_content = chat[0]
            assistant_content = chat[1]

        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=9,
            leading=12,
            leftIndent=36,
            textColor=colors.white,
            backColor=colors.Color(0.1, 0.1, 0.1),  # Dark background (almost black)
            borderPadding=8,
            borderColor=colors.Color(0.15, 0.15, 0.15)  # Slightly lighter border
        ))

        # Create content
        content = []
        
        # Add title
        title = Paragraph("Chat Export", styles['Title'])
        content.append(title)
        content.append(Spacer(1, 12))
        
        # Add timestamp
        timestamp = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        content.append(timestamp)
        content.append(Spacer(1, 24))

        if user_content:
            # Process and add user message
            content.append(Paragraph("User:", styles['Heading2']))
            content.append(Spacer(1, 6))
            user_message = html.escape(user_content)
            content.append(Paragraph(user_message, styles['Normal']))
            content.append(Spacer(1, 12))

        # Process and add assistant message
        content.append(Paragraph("Assistant:", styles['Heading2']))
        content.append(Spacer(1, 6))
        
        # Convert markdown to HTML and handle code blocks
        html_response = markdown2.markdown(assistant_content)
        
        # Extract and process code blocks
        code_pattern = re.compile(r'<pre><code.*?>(.*?)</code></pre>', re.DOTALL)
        last_end = 0
        current_pos = 0
        
        for match in code_pattern.finditer(html_response):
            # Add text before code block
            text_before = html_response[current_pos:match.start()]
            if text_before:
                text_before = html.unescape(text_before)
                content.append(Paragraph(text_before, styles['Normal']))
                content.append(Spacer(1, 6))
            
            # Add code block
            code = html.unescape(match.group(1))
            content.append(Preformatted(code, styles['CodeBlock']))
            content.append(Spacer(1, 6))
            
            current_pos = match.end()
            
        # Add remaining text after last code block
        if current_pos < len(html_response):
            remaining_text = html_response[current_pos:]
            remaining_text = html.unescape(remaining_text)
            content.append(Paragraph(remaining_text, styles['Normal']))

        # Build PDF
        doc.build(content)
        
        # Get PDF from buffer
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='chat_export.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error exporting PDF: {str(e)}")
        return jsonify({'error': 'Failed to export PDF'}), 500

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except OSError:
            return True

def get_process_using_port(port):
    """Get the process ID using the specified port"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            connections = psutil.Process(proc.info['pid']).connections()
            for conn in connections:
                if conn.laddr.port == port:
                    return proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def is_guria_process(process_info):
    """Check if the process is a GURIA app process"""
    if not process_info:
        return False
    
    cmdline = process_info.get('cmdline', [])
    return any('python' in cmd.lower() and 'app.py' in cmd.lower() for cmd in cmdline if cmd)

def find_available_port(start_port=5001, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    raise RuntimeError("Could not find an available port")

def get_local_ip():
    """Get the local IP address"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def get_db():
    return sqlite3.connect('chats.db')

def init_db():
    """Initialize the database."""
    try:
        # First, try to drop the existing table
        conn = get_db()
        cur = conn.cursor()
        cur.execute('DROP TABLE IF EXISTS chats')
        conn.commit()

        # Create the table with the new schema
        cur.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        ''')
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

def initialize_ollama_model(model_name):
    """Initialize and pull the model if not already available"""
    try:
        # Check if model exists
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_exists = any(m['name'] == model_name for m in models)
            
            if not model_exists:
                # Pull the model
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": model_name},
                )
                if response.status_code != 200:
                    raise Exception(f"Failed to pull model: {response.text}")
        
        # Warm up the model with a simple query
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "Hello",
                "stream": False
            },
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to initialize model: {response.text}")
            
        return True
    except Exception as e:
        raise Exception(f"Error initializing model: {str(e)}")

def verify_ssl_certificates(cert_path, key_path):
    """Verify that SSL certificates are valid"""
    try:
        import ssl
        
        logger.info("Verifying SSL certificates...")
        
        # Check if files exist
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            logger.error("Certificate files don't exist")
            return False
            
        # Try to create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(cert_path, key_path)
            logger.info("SSL certificates are valid")
            return True
        except ssl.SSLError as e:
            logger.error(f"Invalid SSL certificates: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error verifying SSL certificates: {str(e)}")
        return False

def generate_ssl_certificates(cert_path, key_path):
    """Generate SSL certificates using mkcert"""
    try:
        ssl_dir = os.path.dirname(cert_path)
        if not os.path.exists(ssl_dir):
            os.makedirs(ssl_dir, exist_ok=True)

        # Remove old certificates if they exist
        if os.path.exists(cert_path):
            os.remove(cert_path)
        if os.path.exists(key_path):
            os.remove(key_path)

        # Run mkcert commands
        logger.info("Installing mkcert root CA...")
        install_result = os.system('mkcert -install')
        if install_result != 0:
            logger.error("Failed to install mkcert root CA")
            return False

        logger.info("Generating certificates...")
        gen_result = os.system(f'mkcert -cert-file "{cert_path}" -key-file "{key_path}" localhost 127.0.0.1 ::1')
        if gen_result != 0:
            logger.error("Failed to generate certificates")
            return False

        return verify_ssl_certificates(cert_path, key_path)
    except Exception as e:
        logger.error(f"Error generating certificates: {str(e)}")
        return False

def shutdown_server():
    """Helper function to shutdown the server"""
    try:
        # Kill Ollama first
        subprocess.run(['pkill', 'ollama'], check=False)
        time.sleep(1)  # Give Ollama time to clean up
        
        # Then shutdown Flask
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
    except Exception as e:
        logger.error(f"Error during server shutdown: {str(e)}")
        raise

@app.route('/goodbye')
def goodbye():
    """Show goodbye page"""
    return render_template('goodbye.html')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Handle server shutdown request"""
    try:
        # Schedule the shutdown
        def delayed_shutdown():
            time.sleep(1)  # Give time for the response to be sent
            shutdown_server()

        Thread(target=delayed_shutdown).start()
        return jsonify({'status': 'success', 'message': 'Server is shutting down'}), 200
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Global flag for shutdown
shutdown_flag = False

def signal_handler(sig, frame):
    """Handle CTRL+C and other termination signals"""
    print("\nInitiating shutdown sequence...")
    
    try:
        print("Stopping Ollama service...")
        subprocess.run(['pkill', 'ollama'], check=False)
        time.sleep(1)  # Give Ollama a moment to clean up
        print("Ollama service stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping Ollama: {str(e)}")
    
    print("Shutting down Guria...")
    try:
        # Clean up database connections
        with app.app_context():
            if hasattr(g, 'db'):
                g.db.close()
                print("Database connections closed")
        
        # Clean up any temporary files
        db_path = os.path.join(os.path.dirname(__file__), 'guria.db')
        if os.path.exists(db_path + '-journal'):
            os.remove(db_path + '-journal')
            print("Temporary database files cleaned up")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
    
    print("Shutdown complete. Goodbye!")
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # CTRL+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination request
    
    def main():
        parser = argparse.ArgumentParser(description='GURIA - Generative Understanding & Responsive Intelligent Assistant')
        parser.add_argument('--port', type=int, default=7860, help='Port to run the server on')
        parser.add_argument('--force-http', action='store_true', help='Force HTTP mode (not recommended)')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode (not recommended for production)')
        args = parser.parse_args()

        # Set Flask environment
        os.environ['FLASK_ENV'] = 'development' if args.debug else 'production'
        app.debug = args.debug

        # Initialize logging
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Initialize the application
        init_app()

        # Initialize the database
        init_db()

        # Check for SSL certificates
        cert_path = os.path.join(os.path.dirname(__file__), 'ssl', 'cert.pem')
        key_path = os.path.join(os.path.dirname(__file__), 'ssl', 'key.pem')
        
        ssl_context = None
        if not args.force_http:
            try:
                # Try to generate certificates
                if generate_ssl_certificates(cert_path, key_path):
                    ssl_context = (cert_path, key_path)
                    logger.info("Successfully set up HTTPS with valid certificates")
                else:
                    logger.warning("Failed to set up HTTPS, falling back to HTTP")
            except Exception as e:
                logger.error(f"Error setting up HTTPS: {str(e)}")
                logger.info("Falling back to HTTP mode")
        
        protocol = 'https' if ssl_context else 'http'
        logger.info(f"Starting GURIA in {protocol.upper()} mode on port {args.port}")
        print(f"\n Starting GURIA in {protocol.upper()} mode {'(debug enabled)' if args.debug else ''}")
        url = f"{protocol}://localhost:{args.port}"
        padding = " " * (40 - len(url))
        print(f"""
        ╭──────────────────────────────────────────╮
        │                                          │
        │   🚀 Access the application at:          │
        │   ✨ {url}{padding}│
        │                                          │
        ╰──────────────────────────────────────────╯
        """)

        if ssl_context:
            print(" Note: If you see a security warning, this is normal for local HTTPS certificates.\n")
        else:
            print(" Note: Running in HTTP mode. This is less secure but suitable for local development.\n")

        try:
            # Clear any existing database lock
            db_path = os.path.join(os.path.dirname(__file__), 'chats.db')
            if os.path.exists(db_path + '-journal'):
                logger.info("Removing stale database journal file")
                os.remove(db_path + '-journal')
        
            app.run(
                host='0.0.0.0',
                port=args.port,
                ssl_context=ssl_context,
                debug=args.debug
            )
        except Exception as e:
            logger.error(f"Error starting Flask app: {str(e)}")
            if 'address already in use' in str(e).lower():
                logger.error(f"Port {args.port} is already in use. Please free up the port and try again.")
            raise

    try:
        main()
    except KeyboardInterrupt:
        # This ensures we don't get an ugly traceback on CTRL+C
        pass
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        # Ensure Ollama is killed even if the app crashes
        subprocess.run(['pkill', 'ollama'], check=False)
        sys.exit(1)
