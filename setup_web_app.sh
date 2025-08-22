#!/bin/bash

echo "🚀 Setting up Crypto Trading Web Application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pricer.py" ]; then
    print_error "Please run this script from the my-pricer directory"
    exit 1
fi

print_status "Setting up backend environment..."

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# No need to cd back to root here as we didn't cd into web/backend


print_status "Setting up frontend environment..."

# Install Node.js dependencies for frontend
cd web/frontend
print_status "Installing Node.js dependencies..."
npm install

# Go back to root
cd ../..

# Create environment files if they don't exist
print_status "Setting up environment configuration..."

if [ ! -f "web/backend/.env" ]; then
    print_warning "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your Auth0 credentials"
fi

if [ ! -f "web/frontend/.env.local" ]; then
    print_warning "Creating frontend .env.local file from template..."
    cp web/frontend/.env.local.example web/frontend/.env.local
    print_warning "Please edit web/frontend/.env.local file with your Auth0 credentials"
fi

# Create data directories
print_status "Creating data directories..."
mkdir -p data/{results,cache,logs}

print_success "Setup completed successfully!"

echo ""
echo "📋 Next Steps:"
echo "1. Configure Auth0:"
echo "   - Edit .env file with your Auth0 credentials"
echo "   - Edit web/frontend/.env.local with your Auth0 credentials"
echo ""
echo "2. Start the backend server:"
echo "   cd web/backend"
echo "   python run.py"
echo ""
echo "3. Start the frontend server (in another terminal):"
echo "   cd web/frontend"
echo "   npm run dev"
echo ""
echo "4. Open your browser to:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:5000"
echo "   Health Check: http://localhost:5000/api/health"
echo ""
echo "🔐 Auth0 Setup Required:"
echo "   - Create Auth0 application"
echo "   - Configure callback URLs"
echo "   - Set environment variables"
echo ""
print_success "Ready to start development!"