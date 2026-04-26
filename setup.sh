#!/usr/bin/env bash
# Investidubh Setup Script
# This script automates the initial setup process for the platform.

set -e

echo -e "\033[1;36m"
echo "========================================================"
echo " 🔍 Investidubh — Commercial-Grade OSINT Platform Setup"
echo "========================================================"
echo -e "\033[0m"

# 1. Dependency checks
command -v docker >/dev/null 2>&1 || { echo >&2 "Error: docker is required but it's not installed. Aborting."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo >&2 "Error: docker-compose is required but it's not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo >&2 "Error: python3 is required for the CLI but it's not installed. Aborting."; exit 1; }

# 2. Environment Setup
echo -e "\n[*] Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    
    # Generate random passwords if requested or just use defaults
    read -p "Do you want to generate secure random passwords for DB and MinIO? (y/n): " gen_pwd
    if [[ "$gen_pwd" == "y" || "$gen_pwd" == "Y" ]]; then
        DB_PWD=$(openssl rand -hex 16)
        MINIO_PWD=$(openssl rand -hex 16)
        JWT_SEC=$(openssl rand -hex 32)
        
        # macOS sed syntax
        sed -i '' "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PWD/" .env
        sed -i '' "s/MINIO_PASSWORD=.*/MINIO_PASSWORD=$MINIO_PWD/" .env
        echo "JWT_SECRET=$JWT_SEC" >> .env
        echo "Generated secure passwords and saved to .env."
    else
        echo "Created .env using default values."
    fi
else
    echo ".env file already exists. Skipping."
fi

# 3. CLI Setup
echo -e "\n[*] Setting up CLI virtual environment..."
python3 -m venv cli/venv
source cli/venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r cli/requirements.txt > /dev/null 2>&1

# Create a convenient wrapper script
cat << 'EOF' > investidubh
#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/cli/venv/bin/activate"
python "$DIR/cli/investidubh_cli.py" "$@"
EOF
chmod +x investidubh
echo "Created CLI wrapper './investidubh'."

# 4. Starting Services
echo -e "\n[*] Starting Docker containers (this may take a few minutes for the first build)..."
docker-compose up -d --build

# Wait for containers to be ready
echo -e "\n[*] Waiting for services to initialize..."
sleep 15

# 5. Database Migration
echo -e "\n[*] Running database migrations..."
if docker-compose ps | grep -q "analysis.*Up"; then
    docker-compose exec -T analysis python src/migrate_db.py || echo "[!] Migration script returned an error, it may have already been run or the DB is not fully ready."
else
    echo "[!] Analysis container is not running. Skipping migration."
fi

echo -e "\033[1;32m"
echo "========================================================"
echo " ✅ Setup Complete!"
echo "========================================================"
echo -e "\033[0m"
echo "Web Dashboard : http://localhost:3000"
echo "API Gateway   : http://localhost:4000/api"
echo "MinIO Console : http://localhost:9001"
echo ""
echo "To use the CLI, you can now run:"
echo "  ./investidubh auth login --username admin --password secret"
echo "  ./investidubh scan https://example.com"
echo "  ./investidubh list"
echo ""
echo "To view logs, run: docker-compose logs -f"
