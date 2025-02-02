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

# Function to check and stop running instances
check_and_stop_instances() {
    local stopped_something=0
    
    # First check for any running Guria processes
    print_step "Checking for running Guria instances..."
    local guria_pids=$(pgrep -f "python.*app.py.*guria")
    
    if [ ! -z "$guria_pids" ]; then
        print_warning "Found running Guria instances. Stopping them..."
        echo "$guria_pids" | while read -r pid; do
            kill -15 "$pid" 2>/dev/null
            if [ $? -eq 0 ]; then
                print_success "Stopped Guria process (PID: $pid)"
                stopped_something=1
            else
                print_error "Failed to stop Guria process (PID: $pid)"
            fi
        done
        sleep 2
    fi
    
    # Then check if port 5000 is in use
    if lsof -i:5000 > /dev/null 2>&1; then
        print_warning "Port 5000 is in use. Checking process..."
        local port_pid=$(lsof -t -i:5000 2>/dev/null)
        
        if [ ! -z "$port_pid" ]; then
            # Check if it's a Guria process
            if ps -p "$port_pid" -o command= | grep -q "guria"; then
                print_warning "Port 5000 is used by another Guria instance. Stopping it..."
                kill -15 "$port_pid" 2>/dev/null
                sleep 2
                if lsof -i:5000 > /dev/null 2>&1; then
                    print_error "Failed to stop Guria process on port 5000"
                    print_step "Using a different port..."
                    export FLASK_RUN_PORT=5001
                else
                    print_success "Successfully stopped Guria process on port 5000"
                    stopped_something=1
                fi
            else
                # If it's not a Guria process, just use a different port
                print_warning "Port 5000 is used by another application"
                print_step "Using port 5001 instead..."
                export FLASK_RUN_PORT=5001
            fi
        fi
    fi
    
    # If we stopped anything, wait a moment to ensure ports are freed
    if [ $stopped_something -eq 1 ]; then
        print_step "Waiting for processes to fully stop..."
        sleep 3
    fi
    
    return 0
}

# Function to check Ollama service
check_ollama() {
    if ! curl -s http://localhost:11434/api/tags > /dev/null; then
        print_warning "Ollama service is not running"
        print_step "Please start Ollama first using:"
        echo -e "${GREEN}${DIM}   ollama serve${NC}"
        return 1
    fi
    print_success "Ollama service is running"
    return 0
}

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

print_header "System Check"
check_python_version || exit 1
check_pip || exit 1
check_ollama

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

# First, check and stop any running instances
check_and_stop_instances || exit 1

print_header "Launching GURIA"
# Set Flask environment
export FLASK_APP="$SCRIPT_DIR/app.py"
export FLASK_ENV=production
export FLASK_DEBUG=0
print_success "Flask environment configured"

print_step "Starting application..."
echo -e "${DIM}Press Ctrl+C to stop the application${NC}\n"

# Ensure we're in the right directory and using the virtual environment's Python
cd "$SCRIPT_DIR" && source venv/bin/activate && python app.py
