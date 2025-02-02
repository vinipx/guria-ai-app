<div align="center">
  <h1>👩‍🤖 GURIA</h1>
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
- 📱 Mobile-friendly design
- 💾 Local chat history storage
- 📤 Export chats to multiple formats (PDF, Markdown, Text)
- 🎯 Multiple Ollama model support
- 🔒 Privacy-focused (all data stays local)
- 🚀 Easy setup with automated installation script
- 💻 Cross-platform support (Windows, macOS, Linux)

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running
- For Windows users:
  - Windows 10/11 with PowerShell
  - WSL (Windows Subsystem for Linux) is supported
- For macOS/Linux users:
  - Terminal access
  - Basic build tools (included in macOS, major Linux distributions)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/vinipx/guria-ai-app.git
cd guria-ai-app
```

2. Run the setup script:

**On Windows:**
```powershell
.\guria
```

**On macOS/Linux:**
```bash
./guria
```

The script will automatically:
- Detect your operating system
- Choose the appropriate setup process
- Create a virtual environment
- Install all dependencies
- Configure the application
- Start the server

### Platform-Specific Notes

#### Windows Users
- Runs natively on Windows using PowerShell
- Also supports WSL if you prefer a Linux environment
- Automatically handles Windows-specific path issues
- Uses PowerShell-styled output for better Windows integration

#### macOS Users
- Native support for both Intel and Apple Silicon
- Automatically configures required environment variables
- Handles macOS-specific library paths

#### Linux Users
- Supports all major Linux distributions
- Uses the same setup process as macOS
- Automatically adjusts paths for Linux environment

## 🛠️ Technology Stack

- **Backend**: Flask 3.0.0
- **Frontend**: HTML5, TailwindCSS, JavaScript
- **AI Integration**: Ollama API
- **Database**: SQLite
- **PDF Generation**: ReportLab
- **Process Management**: psutil

## 🎯 Usage

1. Start Ollama service:
```bash
# Windows/macOS/Linux
ollama serve
```

2. Launch GURIA:
```bash
# Windows
.\guria

# macOS/Linux
./guria
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for providing the amazing AI models
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [TailwindCSS](https://tailwindcss.com/) for the styling system

## 📧 Contact

Vinicius Peixoto - [@vinipx](https://github.com/vinipx)

Project Link: [https://github.com/vinipx/guria-ai-app](https://github.com/vinipx/guria-ai-app)

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/vinipx">Vinicius Peixoto</a></sub>
</div>
