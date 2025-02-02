from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
import requests
import os
import socket
import psutil
import signal
from dotenv import load_dotenv
import time
import sys
import subprocess
from jinja2 import ChoiceLoader, FileSystemLoader
import threading
import json
import sqlite3
from datetime import datetime
import argparse
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
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
def chat():
    # If no model is selected, redirect to model selection
    if 'model' not in session:
        return redirect(url_for('index'))
        
    ollama_running = check_ollama_status()[0]
    return render_template('chat.html',
                         selected_model=session['model'],
                         ollama_running=ollama_running)

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

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "No prompt provided"}), 400

        model = session.get('model')
        if not model:
            return jsonify({"error": "No model selected"}), 400

        prompt = data['prompt']
        logger.info(f"Sending query to model {model}: {prompt[:50]}...")

        # Check Ollama connection first
        ollama_status, error = check_ollama_status()
        if not ollama_status:
            return jsonify({"error": f"Ollama service not available: {error}"}), 503

        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30  # Add timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                
                # Save to database
                try:
                    save_chat(model, prompt, response_text)
                except Exception as e:
                    logger.error(f"Error saving chat: {str(e)}")
                
                return jsonify({"response": response_text})
            else:
                error_msg = f"Ollama returned status code {response.status_code}"
                logger.error(error_msg)
                return jsonify({"error": error_msg}), response.status_code
                
        except requests.exceptions.Timeout:
            error_msg = "Request to Ollama timed out"
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 504
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Ollama service"
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 503
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 500

    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/chat_history')
def chat_history():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, query, timestamp FROM chats ORDER BY timestamp DESC')
        chats = cursor.fetchall()
        return jsonify([{
            'id': chat[0],
            'query': chat[1],
            'timestamp': chat[2]
        } for chat in chats])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear all chat history"""
    clear_chat_history()
    return jsonify({'status': 'success'})

@app.route('/goodbye')
def goodbye():
    """Show goodbye page"""
    return render_template('goodbye.html')

@app.route('/api/shutdown', methods=['POST'])
def initiate_shutdown():
    """First step: Return redirect to goodbye page"""
    try:
        app.logger.info("Initiating shutdown process...")
        redirect_url = url_for('goodbye')
        app.logger.info(f"Redirecting to: {redirect_url}")
        return jsonify({
            "message": "Redirecting to goodbye page...",
            "redirect": redirect_url
        })
    except Exception as e:
        app.logger.error(f"Error during shutdown initiation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/execute_shutdown', methods=['POST'])
def execute_shutdown():
    """Second step: Actually perform the shutdown"""
    try:
        app.logger.info("Executing shutdown...")
        # Get our process ID
        pid = os.getpid()
        app.logger.info(f"Current process ID: {pid}")
        
        # Try to stop Ollama based on platform
        if sys.platform == "win32":
            app.logger.info("Stopping Ollama on Windows...")
            # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], check=False)
        else:
            app.logger.info("Stopping Ollama on Unix-like system...")
            # Unix-like systems (macOS, Linux)
            subprocess.run(['pkill', '-f', 'ollama'], check=False)
        
        # Clear the session
        session.clear()
        app.logger.info("Session cleared")
        
        # Send success response
        response = jsonify({"message": "Server shutting down..."})
        response.headers['Connection'] = 'close'
        app.logger.info("Shutdown response prepared")
        
        # Define a function to kill this process
        def kill_self():
            app.logger.info("Starting kill_self function...")
            time.sleep(2)  # Give more time for response to be sent
            app.logger.info("Executing kill command...")
            if sys.platform == "win32":
                # Windows
                os.kill(pid, signal.CTRL_C_EVENT)
            else:
                # Unix-like systems (macOS, Linux)
                os.kill(pid, signal.SIGTERM)
        
        # Start a thread to kill the server
        thread = threading.Thread(target=kill_self)
        thread.daemon = True
        thread.start()
        app.logger.info("Kill thread started")
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error during shutdown execution: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the application and Ollama service"""
    try:
        # Get our process ID
        pid = os.getpid()
        
        # Try to stop Ollama based on platform
        if sys.platform == "win32":
            # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], check=False)
        else:
            # Unix-like systems (macOS, Linux)
            subprocess.run(['pkill', '-f', 'ollama'], check=False)
        
        # Clear the session
        session.clear()
        
        # Send success response with redirect
        response = jsonify({
            "message": "Server shutting down...",
            "redirect": url_for('goodbye')
        })
        response.headers['Connection'] = 'close'
        
        # Define a function to kill this process
        def kill_self():
            time.sleep(2)  # Give more time for response to be sent
            if sys.platform == "win32":
                # Windows
                os.kill(pid, signal.CTRL_C_EVENT)
            else:
                # Unix-like systems (macOS, Linux)
                os.kill(pid, signal.SIGTERM)
        
        # Start a thread to kill the server
        thread = threading.Thread(target=kill_self)
        thread.daemon = True
        thread.start()
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error during shutdown: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/get_chat', methods=['POST'])
def get_chat():
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        
        if chat_id is None:
            return jsonify({'error': 'No chat_id provided'}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT query, response FROM chats WHERE id = ?', (chat_id,))
        chat = cursor.fetchone()
        
        if chat is None:
            return jsonify({'error': 'Chat not found'}), 404
            
        return jsonify({
            'query': chat[0],
            'response': chat[1]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
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

        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=48,
            leftMargin=48,
            topMargin=48,
            bottomMargin=48
        )

        # Create styles
        styles = getSampleStyleSheet()
        
        # Add custom styles
        custom_styles = {
            'ChatCodeBlock': ParagraphStyle(
                name='ChatCodeBlock',
                parent=styles['Code'],
                fontSize=11,
                leading=14,
                backColor=colors.Color(0.95, 0.95, 0.95),  # Light gray background
                textColor=colors.black,
                fontName='Courier',
                spaceAfter=16,
                spaceBefore=16,
                borderPadding=8,
                borderWidth=1,
                borderColor=colors.Color(0.8, 0.8, 0.8),  # Light gray border
                borderRadius=4
            ),
            'ChatHeading': ParagraphStyle(
                name='ChatHeading',
                parent=styles['Heading1'],  # Using Heading1 as parent to preserve heading properties
                fontSize=16,
                leading=20,
                textColor=colors.black,
                spaceAfter=12,
                spaceBefore=16,
                bold=True,
                keepWithNext=True  # Keep headings with their content
            ),
            'ChatText': ParagraphStyle(
                name='ChatText',
                parent=styles['Normal'],
                fontSize=12,
                leading=16,
                textColor=colors.black,
                spaceAfter=12,
                spaceBefore=0,
                fontName='Helvetica'
            ),
            'InlineCode': ParagraphStyle(
                name='InlineCode',
                parent=styles['Code'],
                fontSize=11,
                textColor=colors.black,
                fontName='Courier',
                backColor=colors.Color(0.95, 0.95, 0.95)  # Light gray background
            )
        }

        def process_text(text):
            # Preserve line breaks
            text = text.replace('\n', '<br/>')
            
            # Handle inline code
            text = re.sub(r'`(.*?)`', 
                       lambda m: f'<span style="font-family: Courier; background-color: #F2F2F2; padding: 2px 4px; border-radius: 3px">{m.group(1)}</span>', 
                       text)
            
            # Handle bold text
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            
            # Handle italic text
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            
            return text

        # Process content
        story = []
        sections = re.split(r'(<h3>.*?</h3>)', content)
        
        for section in sections:
            if section.startswith('<h3>'):
                # Process heading
                heading_text = re.sub(r'<[^>]+>', '', section).strip()
                if heading_text:
                    story.append(Paragraph(heading_text, custom_styles['ChatHeading']))
            else:
                # Convert remaining HTML to markdown and then process
                html_content = markdown2.markdown(section)
                
                # Split content to handle code blocks separately
                parts = re.split(r'(<pre><code>.*?</code></pre>)', html_content, flags=re.DOTALL)
                
                for part in parts:
                    if part.strip():
                        if part.startswith('<pre><code>'):
                            # Process code block
                            code = re.sub(r'<[^>]+>', '', part).strip()
                            if code:
                                story.append(Spacer(1, 8))
                                story.append(Preformatted(code, custom_styles['ChatCodeBlock']))
                                story.append(Spacer(1, 8))
                        else:
                            # Process regular text
                            text = re.sub(r'<pre.*?</pre>', '', part, flags=re.DOTALL)  # Remove any remaining pre tags
                            text = process_text(text)
                            
                            # Split into paragraphs and process each
                            paragraphs = re.split(r'<br\s*/?>', text)
                            for paragraph in paragraphs:
                                paragraph = paragraph.strip()
                                if paragraph:
                                    story.append(Paragraph(paragraph, custom_styles['ChatText']))

        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': 'attachment;filename=chat_export.pdf',
                'Content-Type': 'application/pdf'
            }
        )

    except Exception as e:
        app.logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect('chats.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT NOT NULL,
         model TEXT NOT NULL,
         query TEXT NOT NULL,
         response TEXT NOT NULL)
    ''')
    conn.commit()
    conn.close()

def save_chat(model, query, response):
    """Save a chat interaction to the database"""
    conn = sqlite3.connect('chats.db')
    c = conn.cursor()
    c.execute('INSERT INTO chats (timestamp, model, query, response) VALUES (?, ?, ?, ?)',
              (datetime.now().isoformat(), model, query, response))
    conn.commit()
    conn.close()

def get_chat_history():
    """Retrieve all chat history"""
    conn = sqlite3.connect('chats.db')
    c = conn.cursor()
    c.execute('SELECT * FROM chats ORDER BY timestamp DESC')
    chats = [{'id': row[0], 'timestamp': row[1], 'model': row[2], 
              'query': row[3], 'response': row[4]} for row in c.fetchall()]
    conn.close()
    return chats

def clear_chat_history():
    """Clear all chat history"""
    conn = sqlite3.connect('chats.db')
    c = conn.cursor()
    c.execute('DELETE FROM chats')
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect('chats.db')

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
    print(f"   Access the application at: {protocol}://localhost:{args.port}\n")

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

if __name__ == '__main__':
    main()
