#!/bin/bash

# AI Code Review Arena - Quick Start Script

echo "🚀 AI Code Review Arena - Quick Start"
echo "======================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env created. You can edit it to add API keys."
fi

# Ask user for deployment method
echo ""
echo "Choose deployment method:"
echo "  1) Docker Compose (recommended)"
echo "  2) Local development"
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo "🐳 Starting with Docker Compose..."
        docker-compose up -d

        echo ""
        echo "⏳ Waiting for services to be healthy..."
        sleep 10

        echo ""
        echo "✅ Application is running!"
        echo ""
        echo "📱 Frontend: http://localhost:3000"
        echo "🔧 Backend API: http://localhost:8000"
        echo "📚 API Docs: http://localhost:8000/docs"
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop: docker-compose down"
        ;;

    2)
        echo ""
        echo "💻 Starting local development..."

        # Start Redis
        echo "Starting Redis..."
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes
            echo "✅ Redis started"
        else
            echo "⚠️  Redis not found. Install it or the app will use in-memory cache."
        fi

        # Backend
        echo ""
        echo "Setting up backend..."
        cd backend

        if [ ! -d "venv" ]; then
            echo "Creating Python virtual environment..."
            python -m venv venv
        fi

        source venv/bin/activate  # On Windows use: venv\Scripts\activate

        echo "Installing backend dependencies..."
        pip install -q -r requirements.txt

        echo "Running database migrations..."
        alembic upgrade head

        echo "Creating sample data..."
        python scripts/init_db.py

        echo "Starting backend server..."
        uvicorn app.main:app --reload --port 8000 &
        BACKEND_PID=$!

        cd ..

        # Frontend
        echo ""
        echo "Setting up frontend..."
        cd frontend

        if [ ! -d "node_modules" ]; then
            echo "Installing frontend dependencies..."
            npm install
        fi

        if [ ! -f .env ]; then
            cp .env.example .env
        fi

        echo "Starting frontend dev server..."
        npm run dev &
        FRONTEND_PID=$!

        cd ..

        echo ""
        echo "✅ Application is running!"
        echo ""
        echo "📱 Frontend: http://localhost:3000"
        echo "🔧 Backend API: http://localhost:8000"
        echo "📚 API Docs: http://localhost:8000/docs"
        echo ""
        echo "Demo credentials:"
        echo "  Email: demo@example.com"
        echo "  Password: demo123"
        echo ""
        echo "Press Ctrl+C to stop all services"

        # Wait for user interrupt
        trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
        wait
        ;;

    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
