#!/bin/bash

echo "🚀 Starting Crypto Trading Web Application Development Servers..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if environment files exist
if [ ! -f ".env" ]; then
    print_warning "No .env file found. Please run setup_web_app.sh first"
    exit 1
fi

if [ ! -f "web/frontend/.env.local" ]; then
    print_warning "No frontend .env.local file found. Please run setup_web_app.sh first"
    exit 1
fi

# Function to start backend
start_backend() {
    print_info "Starting Flask backend server..."
    cd web/backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Please run setup_web_app.sh first"
        exit 1
    fi
    
    # Activate virtual environment and start server
    source venv/bin/activate
    python run.py &
    BACKEND_PID=$!
    
    cd ../..
    print_success "Backend server started (PID: $BACKEND_PID)"
}

# Function to start frontend
start_frontend() {
    print_info "Starting Next.js frontend server..."
    cd web/frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "Node modules not found. Please run setup_web_app.sh first"
        exit 1
    fi
    
    npm run dev &
    FRONTEND_PID=$!
    
    cd ../..
    print_success "Frontend server started (PID: $FRONTEND_PID)"
}

# Function to cleanup on exit
cleanup() {
    print_info "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        print_info "Backend server stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        print_info "Frontend server stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start servers
start_backend
sleep 2
start_frontend

print_success "Both servers are starting up..."
echo ""
echo "📡 Server URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:5000"
echo "   Health Check: http://localhost:5000/api/health"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user to stop
wait
