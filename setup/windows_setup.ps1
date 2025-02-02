# Windows Setup Script for GURIA
param (
    [string]$ScriptDir
)

# Colors for Windows PowerShell
$Yellow = [System.ConsoleColor]::Yellow
$Green = [System.ConsoleColor]::Green
$Red = [System.ConsoleColor]::Red
$Cyan = [System.ConsoleColor]::Cyan
$White = [System.ConsoleColor]::White

# Function to print colored messages
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Print-Header($message) {
    Write-ColorOutput $Yellow "`n▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀"
    Write-ColorOutput $Yellow "  $message"
    Write-ColorOutput $Yellow "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄`n"
}

function Print-Step($message) {
    Write-ColorOutput $Cyan "→ $message"
}

function Print-Success($message) {
    Write-ColorOutput $Green "✓ $message"
}

function Print-Error($message) {
    Write-ColorOutput $Red "✗ $message"
    return $false
}

# Function to check Python version
function Check-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match '(\d+)\.(\d+)\.(\d+)') {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Print-Success "Python $pythonVersion is installed"
                return $true
            }
        }
        Print-Error "Python 3.8 or higher is required"
        return $false
    }
    catch {
        Print-Error "Python is not installed"
        return $false
    }
}

# Function to check pip installation
function Check-Pip {
    try {
        pip --version | Out-Null
        Print-Success "pip is installed"
        return $true
    }
    catch {
        Print-Error "pip is not installed"
        return $false
    }
}

# Function to create and activate virtual environment
function Setup-Venv {
    if (-not (Test-Path "venv")) {
        Print-Step "Creating virtual environment..."
        python -m venv venv
    }
    
    Print-Step "Activating virtual environment..."
    try {
        & .\venv\Scripts\Activate.ps1
        Print-Success "Virtual environment activated"
        return $true
    }
    catch {
        Print-Error "Failed to activate virtual environment"
        return $false
    }
}

# Function to install Python dependencies
function Install-Dependencies {
    Print-Step "Checking dependencies..."
    
    if (-not (Test-Path "requirements.txt")) {
        Print-Error "requirements.txt not found"
        Print-Step "Creating requirements.txt..."
        @"
flask==3.0.0
flask-cors==4.0.0
reportlab==4.2.5
markdown2==2.5.3
Pillow==10.4.0
requests==2.31.0
python-dotenv==1.0.0
chardet==4.0.0
psutil==5.9.8
"@ | Out-File -FilePath "requirements.txt" -Encoding UTF8
    }
    
    Print-Step "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Dependencies installed successfully"
        return $true
    }
    else {
        Print-Error "Failed to install dependencies"
        return $false
    }
}

# Function to check Ollama service
function Check-Ollama {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Print-Success "Ollama service is running"
            return $true
        }
    }
    catch {
        Print-Warning "Ollama service is not running"
        Print-Step "Please start Ollama first using:"
        Write-ColorOutput $Green "   ollama serve"
        return $false
    }
}

# Function to check and stop running instances
function Check-And-Stop-Instances {
    $stoppedSomething = $false
    
    # Check for running Python processes
    Print-Step "Checking for running Guria instances..."
    $guriaPids = Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*app.py*guria*" } | Select-Object -ExpandProperty Id
    
    foreach ($pid in $guriaPids) {
        Print-Warning "Found running Guria instance. Stopping process ID: $pid"
        try {
            Stop-Process -Id $pid -Force
            Print-Success "Stopped Guria process (PID: $pid)"
            $stoppedSomething = $true
        }
        catch {
            Print-Error "Failed to stop Guria process (PID: $pid)"
        }
    }
    
    # Check if port 5000 is in use
    try {
        $port5000 = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
        if ($port5000) {
            $process = Get-Process -Id $port5000.OwningProcess
            if ($process.ProcessName -like "*python*" -and $process.CommandLine -like "*guria*") {
                Print-Warning "Port 5000 is used by another Guria instance. Stopping it..."
                Stop-Process -Id $port5000.OwningProcess -Force
                Start-Sleep -Seconds 2
                Print-Success "Successfully stopped Guria process on port 5000"
                $stoppedSomething = $true
            }
            else {
                Print-Warning "Port 5000 is used by another application"
                Print-Step "Using port 5001 instead..."
                $env:FLASK_RUN_PORT = 5001
            }
        }
    }
    catch {
        # Port is free
    }
    
    if ($stoppedSomething) {
        Print-Step "Waiting for processes to fully stop..."
        Start-Sleep -Seconds 3
    }
    
    return $true
}

# Main setup process
Print-Header "System Check"
if (-not (Check-PythonVersion)) { exit 1 }
if (-not (Check-Pip)) { exit 1 }
Check-Ollama

Print-Header "Environment Setup"
if (-not (Setup-Venv)) { exit 1 }
if (-not (Install-Dependencies)) { exit 1 }

Print-Header "Application Setup"
# Set Flask environment
$env:FLASK_APP = Join-Path $ScriptDir "app.py"
$env:FLASK_ENV = "production"
$env:FLASK_DEBUG = "0"
Print-Success "Flask environment configured"

Check-And-Stop-Instances

Print-Header "Launching GURIA"
Print-Step "Starting application..."
Write-ColorOutput $White "Press Ctrl+C to stop the application`n"
python app.py
