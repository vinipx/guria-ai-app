#!/bin/bash

# Colors and formatting
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Function to print a section header
print_header() {
    echo -e "\n${YELLOW}${BOLD}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀${NC}"
    echo -e "${YELLOW}${BOLD}  $1${NC}"
    echo -e "${YELLOW}${BOLD}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${NC}\n"
}

# Function to print a step
print_step() {
    echo -e "${CYAN}${BOLD}→${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}${BOLD}✓${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}${BOLD}✗${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}${BOLD}!${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        python_version=$(python3 -V 2>&1 | cut -d' ' -f2)
        major_version=$(echo $python_version | cut -d. -f1)
        minor_version=$(echo $python_version | cut -d. -f2)
        
        if [ "$major_version" -ge 3 ] && [ "$minor_version" -ge 8 ]; then
            print_success "Python $python_version is installed"
            return 0
        fi
    fi
    print_error "Python 3.8 or higher is required"
    return 1
}

# Function to check pip installation
check_pip() {
    if command_exists pip3; then
        print_success "pip3 is installed"
        return 0
    fi
    print_error "pip3 is not installed"
    return 1
}

# Function to create and activate virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        print_step "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    print_step "Activating virtual environment..."
    source venv/bin/activate
    
    if [ $? -eq 0 ]; then
        print_success "Virtual environment activated"
        return 0
    else
        print_error "Failed to activate virtual environment"
        return 1
    fi
}

# Function to check if a Python package is installed
check_package() {
    python3 -c "import pkg_resources; pkg_resources.require('$1')" 2>/dev/null
    return $?
}

# Function to check requirements file
check_requirements_file() {
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        print_step "Creating requirements.txt..."
        cat > requirements.txt << EOF
flask==3.0.0
flask-cors==4.0.0
reportlab==4.2.5
markdown2==2.5.3
Pillow==10.4.0
requests==2.31.0
python-dotenv==1.0.0
chardet==4.0.0
psutil==5.9.8
EOF
        if [ $? -eq 0 ]; then
            print_success "Created requirements.txt"
            return 0
        else
            print_error "Failed to create requirements.txt"
            return 1
        fi
    fi
    return 0
}

# Function to install Python dependencies
install_dependencies() {
    print_step "Checking dependencies..."
    
    # First check if requirements.txt exists
    check_requirements_file || return 1
    
    # Read requirements file and check each package
    local missing_packages=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue
        
        # Extract package name without version
        package_name=$(echo "$line" | cut -d'=' -f1)
        if ! check_package "$package_name"; then
            missing_packages+=("$line")
        fi
    done < requirements.txt
    
    # If no packages are missing, we're done
    if [ ${#missing_packages[@]} -eq 0 ]; then
        print_success "All dependencies are already installed"
        return 0
    fi
    
    # Install missing packages
    print_step "Installing missing dependencies..."
    for package in "${missing_packages[@]}"; do
        print_step "Installing $package..."
        pip install "$package"
        if [ $? -ne 0 ]; then
            print_error "Failed to install $package"
            return 1
        fi
    done
    
    print_success "Dependencies installed successfully"
    return 0
}

# Function to find all Ollama-related processes with PIDs and process info
find_ollama_processes_info() {
    # Get detailed process info including parent PIDs and command
    ps aux | grep -E '[o]llama' || true
}

# Function to find just Ollama PIDs
find_ollama_pids() {
    ps aux | grep -E '[o]llama' | awk '{print $2}' || true
}

# Function to stop Ollama.app and its processes
stop_ollama() {
    echo -e "${YELLOW}Attempting to stop Ollama...${NC}"
    
    # First, try to quit Ollama.app if it's running
    if pgrep -f "Ollama.app" >/dev/null; then
        echo -e "${YELLOW}Found Ollama.app, attempting to quit...${NC}"
        osascript -e 'tell application "Ollama" to quit' 2>/dev/null || true
        sleep 2
    fi
    
    # Try graceful shutdown via API
    if curl -s -X POST "http://localhost:11434/api/shutdown" >/dev/null 2>&1; then
        echo -e "${GREEN}Sent shutdown request to Ollama API${NC}"
        sleep 3
    fi
    
    # Get all Ollama-related processes
    local OLLAMA_PROCESSES=$(ps aux | grep -E "Ollama.app|ollama serve" | grep -v grep || true)
    
    if [ ! -z "$OLLAMA_PROCESSES" ]; then
        echo -e "${YELLOW}Current Ollama processes:${NC}"
        echo "$OLLAMA_PROCESSES"
        
        # Get parent process first (Ollama.app)
        local PARENT_PID=$(echo "$OLLAMA_PROCESSES" | grep "Ollama.app" | grep -v "Resources" | awk '{print $2}' || true)
        
        # Get child processes (ollama serve)
        local CHILD_PIDS=$(echo "$OLLAMA_PROCESSES" | grep "ollama serve" | awk '{print $2}' || true)
        
        # Try to stop parent process first
        if [ ! -z "$PARENT_PID" ]; then
            echo -e "${YELLOW}Stopping Ollama.app (PID: $PARENT_PID)...${NC}"
            sudo kill -15 "$PARENT_PID" 2>/dev/null || true
            sleep 2
        fi
        
        # Check if processes are still running
        OLLAMA_PROCESSES=$(ps aux | grep -E "Ollama.app|ollama serve" | grep -v grep || true)
        if [ ! -z "$OLLAMA_PROCESSES" ]; then
            echo -e "${YELLOW}Some processes still running, using force kill...${NC}"
            
            # Force kill all remaining processes
            echo "$OLLAMA_PROCESSES" | awk '{print $2}' | while read -r pid; do
                echo -e "${YELLOW}Force killing PID: $pid${NC}"
                sudo kill -9 "$pid" 2>/dev/null || true
            done
            sleep 2
            
            # If still running, try pkill with sudo
            OLLAMA_PROCESSES=$(ps aux | grep -E "Ollama.app|ollama serve" | grep -v grep || true)
            if [ ! -z "$OLLAMA_PROCESSES" ]; then
                echo -e "${YELLOW}Using pkill as last resort...${NC}"
                sudo pkill -9 -f "Ollama.app" || true
                sudo pkill -9 ollama || true
                sleep 2
            fi
        fi
    fi
    
    # Final check
    if ! pgrep -f "Ollama.app" >/dev/null && ! pgrep -f "ollama serve" >/dev/null; then
        echo -e "${GREEN}All Ollama processes stopped${NC}"
        
        # Clean up port 11434 if still in use
        local PORT_PID=$(lsof -i :11434 -t 2>/dev/null || true)
        if [ ! -z "$PORT_PID" ]; then
            echo -e "${YELLOW}Cleaning up port 11434...${NC}"
            sudo kill -9 $PORT_PID 2>/dev/null || true
        fi
        
        return 0
    else
        echo -e "${RED}Failed to stop all Ollama processes. Current processes:${NC}"
        ps aux | grep -E "Ollama.app|ollama serve" | grep -v grep || true
        echo -e "${YELLOW}Please try closing Ollama.app manually and then run:${NC}"
        echo -e "${YELLOW}sudo pkill -9 -f Ollama.app${NC}"
        echo -e "${YELLOW}sudo pkill -9 ollama${NC}"
        return 1
    fi
}

# Function to stop all running instances
stop_instances() {
    echo -e "${BLUE}Stopping GURIA and Ollama...${NC}"
    local failed=0
    
    # Stop GURIA server first
    local GURIA_PIDS=$(ps aux | grep "[p]ython.*app.py" | awk '{print $2}')
    if [ ! -z "$GURIA_PIDS" ]; then
        echo -e "${YELLOW}Stopping GURIA server...${NC}"
        echo "$GURIA_PIDS" | while read -r pid; do
            kill -9 "$pid" 2>/dev/null || true
        done
    fi
    
    # Check if GURIA processes are still running
    sleep 1
    if pgrep -f "python.*app.py" >/dev/null; then
        echo -e "${RED}Failed to stop GURIA server${NC}"
        failed=1
    else
        echo -e "${GREEN}GURIA server stopped${NC}"
    fi
    
    # Stop Ollama if running
    if pgrep -f "Ollama.app" >/dev/null || pgrep -f "ollama serve" >/dev/null; then
        if ! stop_ollama; then
            failed=1
        fi
    fi
    
    if [ $failed -eq 1 ]; then
        echo -e "${RED}Some processes could not be stopped${NC}"
        return 1
    else
        echo -e "${GREEN}All processes successfully stopped${NC}"
        sleep 2
        return 0
    fi
}

# Function to check and stop running instances
check_and_stop_instances() {
    # Check for running instances
    if pgrep -f "python.*app.py" >/dev/null || pgrep -f "Ollama.app" >/dev/null || pgrep -f "ollama serve" >/dev/null; then
        echo -e "${YELLOW}Found running instances of GURIA or Ollama${NC}"
        if ! stop_instances; then
            return 1
        fi
    fi
    return 0
}

# Function to ensure Ollama is stopped
ensure_ollama_stopped() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if pgrep -f "Ollama.app" >/dev/null || pgrep -f "ollama serve" >/dev/null; then
            echo -e "${YELLOW}Attempt $attempt/$max_attempts to stop Ollama...${NC}"
            
            # Try to stop with sudo directly
            sudo pkill -9 -f "Ollama.app" 2>/dev/null || true
            sudo pkill -9 ollama 2>/dev/null || true
            sleep 2
            
            if ! pgrep -f "Ollama.app" >/dev/null && ! pgrep -f "ollama serve" >/dev/null; then
                echo -e "${GREEN}Ollama successfully stopped${NC}"
                return 0
            fi
        else
            echo -e "${GREEN}No Ollama processes found${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}Failed to stop Ollama after $max_attempts attempts${NC}"
    return 1
}

# Function to check if Ollama is running and responding
check_ollama() {
    # First check if process exists
    if pgrep -f "Ollama.app" >/dev/null || pgrep -f "ollama serve" >/dev/null; then
        return 0
    fi
    
    # Then check if it's responding to API calls
    if ! curl -s -f "http://localhost:11434/api/tags" >/dev/null 2>&1; then
        return 2
    fi
    
    return 0
}

# Function to start Ollama service
start_ollama() {
    echo -e "${BLUE}Starting Ollama service...${NC}"
    
    # Check if Ollama.app is installed
    if [ -d "/Applications/Ollama.app" ]; then
        echo -e "${YELLOW}Found Ollama.app, launching...${NC}"
        open -a Ollama
        
        # Wait for the service to be ready
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            echo -ne "${BLUE}Waiting for Ollama service to start... ($attempt/$max_attempts)${NC}\r"
            
            if curl -s -f "http://localhost:11434/api/tags" >/dev/null 2>&1; then
                echo -e "\n${GREEN}Ollama service is now running${NC}"
                return 0
            fi
            
            sleep 1
            attempt=$((attempt + 1))
        done
        
        echo -e "\n${RED}Failed to start Ollama via app${NC}"
    fi
    
    # If app launch failed or app not found, try CLI
    echo -e "${YELLOW}Starting Ollama via command line...${NC}"
    ollama serve >/dev/null 2>&1 &
    
    # Wait for the service to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo -ne "${BLUE}Waiting for Ollama service to start... ($attempt/$max_attempts)${NC}\r"
        
        if curl -s -f "http://localhost:11434/api/tags" >/dev/null 2>&1; then
            echo -e "\n${GREEN}Ollama service is now running${NC}"
            return 0
        fi
        
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "\n${RED}Failed to start Ollama service${NC}"
    return 1
}

# Function to ensure Ollama is running
ensure_ollama_running() {
    echo -e "${BLUE}Checking Ollama service...${NC}"
    
    # Check if service is responding
    if curl -s -f "http://localhost:11434/api/tags" >/dev/null 2>&1; then
        echo -e "${GREEN}Ollama service is already running${NC}"
        return 0
    fi
    
    # If not responding but processes exist, stop them
    if pgrep -f "Ollama.app" >/dev/null || pgrep -f "ollama serve" >/dev/null; then
        echo -e "${YELLOW}Found non-responding Ollama processes, restarting...${NC}"
        stop_ollama
        sleep 2
    fi
    
    # Start Ollama
    start_ollama
    return $?
}

# Function to display shutdown message
display_shutdown_message() {
    echo
    echo "🌟 Thank you for using GURIA! 🌟"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔹 The application has been gracefully shutdown"
    echo "🔹 All services have been stopped properly"
    echo "🔹 Your chat history is safely stored"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "See you next time! 👋"
    echo
}

# Function to handle graceful shutdown
cleanup() {
    display_shutdown_message
    print_step "Stopping Ollama processes..."
    ensure_ollama_stopped
    print_success "Shutdown complete"
    exit 0
}

# Trap SIGTERM and SIGINT
trap 'cleanup' SIGTERM SIGINT

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print banner
clear
echo -e "${YELLOW}${BOLD}"
echo " ██████╗ ██╗   ██╗██████╗ ██╗ █████╗ "
echo "██╔════╝ ██║   ██║██╔══██╗██║██╔══██╗"
echo "██║  ███╗██║   ██║██████╔╝██║███████║"
echo "██║   ██║██║   ██║██╔══██╗██║██╔══██║"
echo "╚██████╔╝╚██████╔╝██║  ██║██║██║  ██║"
echo " ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "${YELLOW}${BOLD}Generative Understanding & Reasoning Intelligence Assistant${NC}"
echo -e "${DIM}Version 1.0.0${NC}"
echo ""

print_header "Process Check"
check_and_stop_instances || exit 1

print_header "System Check"
check_python_version || exit 1
check_pip || exit 1

print_header "Ollama Service"
ensure_ollama_running || exit 1

print_header "Environment Setup"
setup_venv || exit 1
install_dependencies || exit 1

print_header "Application Setup"
# Set library paths
export DYLD_LIBRARY_PATH="/usr/local/lib:$DYLD_LIBRARY_PATH"
export LIBRARY_PATH="/usr/local/lib:$LIBRARY_PATH"
export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
print_success "Environment variables configured"

# Function to check if openssl is installed
check_openssl() {
    print_step "Checking OpenSSL installation..."
    if ! command_exists "openssl"; then
        print_warning "OpenSSL not found. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install openssl
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command_exists "apt-get"; then
                sudo apt-get update && sudo apt-get install -y openssl
            elif command_exists "yum"; then
                sudo yum install -y openssl
            elif command_exists "dnf"; then
                sudo dnf install -y openssl
            else
                print_error "Could not install OpenSSL. Please install it manually."
                return 1
            fi
        fi
    fi
    print_success "OpenSSL is installed"
    return 0
}

# Function to check if mkcert is installed
check_mkcert() {
    print_step "Checking mkcert installation..."
    if ! command_exists "mkcert"; then
        print_warning "mkcert not found. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install mkcert
            brew install nss # for Firefox support
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command_exists "apt-get"; then
                sudo apt-get update && sudo apt-get install -y libnss3-tools
                curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
                chmod +x mkcert-v*-linux-amd64
                sudo cp mkcert-v*-linux-amd64 /usr/local/bin/mkcert
                rm mkcert-v*-linux-amd64
            else
                print_error "Could not install mkcert. Please install it manually from https://github.com/FiloSottile/mkcert"
                return 1
            fi
        fi
    fi
    print_success "mkcert is installed"
    return 0
}

# Function to generate SSL certificate using mkcert
generate_ssl_certificate() {
    local ssl_dir="$SCRIPT_DIR/ssl"
    local cert_file="$ssl_dir/cert.pem"
    local key_file="$ssl_dir/key.pem"

    print_step "Setting up SSL certificates..."

    # Check mkcert installation
    check_mkcert || {
        print_warning "Falling back to self-signed certificates..."
        generate_self_signed_certificate
        return
    }

    # Create SSL directory if it doesn't exist
    mkdir -p "$ssl_dir"

    # Only generate if certificates don't exist
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        print_step "Generating trusted SSL certificate for secure HTTPS..."
        
        # Install local CA if not already installed
        mkcert -install

        # Generate certificate
        cd "$ssl_dir" && mkcert -key-file key.pem -cert-file cert.pem localhost 127.0.0.1 ::1
        
        print_success "Trusted SSL certificate generated successfully"
        print_success "Your browser should now show a secure connection!"
    else
        print_success "SSL certificate already exists"
    fi
    return 0
}

# Function to generate self-signed certificate (fallback)
generate_self_signed_certificate() {
    local ssl_dir="$SCRIPT_DIR/ssl"
    local cert_file="$ssl_dir/cert.pem"
    local key_file="$ssl_dir/key.pem"

    print_step "Setting up self-signed SSL certificates..."

    # Check OpenSSL installation
    check_openssl || return 1

    # Create SSL directory if it doesn't exist
    mkdir -p "$ssl_dir"

    # Only generate if certificates don't exist
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        print_step "Generating self-signed SSL certificate..."
        if ! openssl req -x509 -newkey rsa:4096 -nodes \
            -out "$cert_file" \
            -keyout "$key_file" \
            -days 365 \
            -subj "/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null; then
            print_error "Failed to generate SSL certificates"
            return 1
        fi
        print_success "Self-signed SSL certificate generated successfully"
        print_warning "Note: Your browser will show a security warning - this is normal for self-signed certificates"
    else
        print_success "SSL certificate already exists"
    fi
    return 0
}

# Function to check and kill existing GURIA processes on a given port
check_and_kill_existing_process() {
    local port=$1
    # Get all PIDs using the port
    local pids=$(lsof -t -i ":$port" 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        print_step "Found processes using port $port: $pids"
        print_step "Stopping processes..."
        # Kill all processes using the port
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null
        done
        sleep 2
        
        # Verify port is free
        if lsof -i ":$port" >/dev/null 2>&1; then
            print_error "Failed to free up port $port"
            return 1
        else
            print_success "Port $port is now free"
            return 0
        fi
    fi
    return 0
}

# Generate SSL certificates
generate_ssl_certificate || exit 1

print_header "Launching GURIA"
# Set Flask environment variables
export FLASK_APP="$SCRIPT_DIR/app.py"
export FLASK_ENV=production
export FLASK_DEBUG=0
print_success "Flask environment configured"

print_step "Checking for existing GURIA processes..."
check_and_kill_existing_process 7860 || exit 1

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --http)
            USE_HTTP=true
            shift
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set default port if not specified
PORT=${PORT:-7860}

print_step "Starting application..."
echo -e "${DIM}Press Ctrl+C to stop the application${NC}\n"

# Build the command with appropriate flags
CMD="cd \"$SCRIPT_DIR\" && source venv/bin/activate && python \"$SCRIPT_DIR/app.py\" --port \"$PORT\""
if [ "$USE_HTTP" = true ]; then
    CMD="$CMD --force-http"
fi
if [ "$DEBUG_MODE" = true ]; then
    CMD="$CMD --debug"
fi

# Run the command
eval "$CMD"
