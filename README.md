<div align="center">
  <img src="static/images/logo.png" alt="GURIA Logo" width="800"/>
  <p><strong>Generative Understanding & Responsive Intelligent Assistant</strong></p>
  <p><i>A powerful and intuitive chat interface for Ollama models</i></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
  [![Flask Version](https://img.shields.io/badge/flask-3.0.0-green)](https://flask.palletsprojects.com/)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
  [![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/vinipx/guria-ai-app/graphs/commit-activity)
  [![Platform](https://img.shields.io/badge/platform-windows%20|%20macos%20|%20linux-lightgrey)](https://github.com/vinipx/guria-ai-app)
</div>

---

## 🌟 Features

- 🎨 Modern, responsive UI with dark mode support
- 🔄 Real-time chat interface with streaming responses
- 🔒 Secure HTTPS with auto-generated SSL certificates
- 📱 Mobile-friendly design
- 💾 Local chat history storage
- 📤 Export chats to multiple formats (PDF, Markdown, Text)
- 🎯 Multiple Ollama model support
- 🔐 Privacy-focused (all data stays local)
- 🚀 Easy setup with automated installation script
- 💻 Cross-platform support (Windows, macOS, Linux)

## 🚀 Quick Start

GURIA comes with a smart setup script that handles everything for you! No need to manually install prerequisites - the script will check and install what's needed.

1. Clone the repository:
```bash
git clone https://github.com/vinipx/guria-ai-app.git
cd guria-ai-app
```

2. Run GURIA:

**On Windows:**
```powershell
.\guria
```

**On macOS/Linux:**
```bash
./guria
```

That's it! The script will automatically:
- Check and install prerequisites (Python, Ollama, etc.)
- Set up the virtual environment
- Install all dependencies
- Generate SSL certificates for secure HTTPS
- Configure the application
- Start the server

Your default web browser will open to `https://localhost:7860` when everything is ready.

> **Note**: Your browser may show a security warning on first access because we use a local certificate for development. This is normal and safe to proceed.

### Platform Support

GURIA works seamlessly across all major platforms:
- ✅ **Windows**: Native support via PowerShell (Windows 10/11)
- ✅ **macOS**: Full support for both Intel and Apple Silicon
- ✅ **Linux**: Compatible with all major distributions
- ✅ **WSL**: Windows Subsystem for Linux supported

## 🎯 Usage

Just run the GURIA script and you're good to go:
```bash
# Windows
.\guria

# macOS/Linux
./guria
```

The script will ensure Ollama is running and handle everything else for you!

## 🛠️ Technology Stack

- **Backend**: Flask 3.0.0
- **Frontend**: HTML5, TailwindCSS, JavaScript
- **AI Integration**: Ollama API
- **Database**: SQLite
- **PDF Generation**: ReportLab
- **Process Management**: psutil

## 🔧 Configuration

GURIA is designed to work out of the box, but you can customize:

- Port number (default: 5000)
- Ollama API endpoint (default: http://localhost:11434)
- Available models (automatically detected from Ollama)
- Export formats and styling

## 📦 Project Structure

```
guria-ai-app/
├── app.py              # Main Flask application
├── templates/          # HTML templates
├── static/            # Static assets
├── setup/             # OS-specific setup scripts
│   ├── mac_setup.sh   # macOS/Linux setup
│   └── windows_setup.ps1  # Windows setup
├── guria              # Main setup script
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Running the Application

GURIA runs in production mode by default with HTTPS enabled. Here are the available options:

```bash
./guria.sh                     # Run in production mode with HTTPS
./guria.sh --http             # Force HTTP mode
./guria.sh --debug            # Enable debug mode
./guria.sh --port 8443        # Use custom port
```

You can combine multiple options:
```bash
./guria.sh --http --debug --port 8080
```

For development and troubleshooting, you can enable debug mode with the `--debug` flag. However, debug mode should never be used in production as it may expose sensitive information.

## HTTP vs HTTPS

GURIA runs in HTTPS mode by default for enhanced security. The application will automatically generate and install SSL certificates using `mkcert` if they don't exist.

If certificate generation fails or if you specifically need HTTP mode, you can force HTTP using the `--http` flag:

```bash
./guria.sh --http
```

You can also specify a custom port:

```bash
./guria.sh --port 8443  # Run with HTTPS on port 8443
./guria.sh --http --port 8080  # Run with HTTP on port 8080
```

Note: When running in HTTPS mode for the first time, you might see a security warning in your browser. This is normal for locally-generated certificates and you can safely proceed.

## 👨‍💻 Authors

Vinicius Peixoto Fagundes - [@vinipx](https://github.com/vinipx)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Ollama](https://ollama.ai/) for providing the amazing AI models
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [TailwindCSS](https://tailwindcss.com/) for the styling system

## 📧 Contact

Vinicius Peixoto Fagundes - [@vinipx](https://github.com/vinipx)

Project Link: [https://github.com/vinipx/guria-ai-app](https://github.com/vinipx/guria-ai-app)

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/vinipx">Vinicius Peixoto Fagundes</a></sub>
</div>
