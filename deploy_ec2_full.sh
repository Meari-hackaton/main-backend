#!/bin/bash

# EC2 전체 배포 스크립트 (PostgreSQL 포함)
# 사용법: ./deploy_ec2_full.sh <EC2_PUBLIC_IP>

if [ -z "$1" ]; then
    echo "Usage: ./deploy_ec2_full.sh <EC2_PUBLIC_IP>"
    exit 1
fi

EC2_IP=$1
KEY_PATH="~/Downloads/meari-backend-key.pem"

echo "🚀 Starting full EC2 deployment to $EC2_IP"

# 1. SSH 키 권한 설정
chmod 400 $KEY_PATH

# 2. 백엔드 파일 압축
echo "📦 Preparing backend files..."
tar -czf meari-backend.tar.gz \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="*.pyc" \
    --exclude=".env" \
    .

# 3. EC2로 파일 전송
echo "📤 Uploading files to EC2..."
scp -i $KEY_PATH meari-backend.tar.gz ubuntu@$EC2_IP:~/
scp -i $KEY_PATH .env ubuntu@$EC2_IP:~/
scp -i $KEY_PATH meari_db_dump.sql ubuntu@$EC2_IP:~/

# 4. EC2 서버 설정
echo "🔧 Configuring EC2 server..."
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'ENDSSH'
    set -e
    
    echo "📦 Updating system packages..."
    sudo apt update
    sudo apt upgrade -y

    echo "🐍 Installing Python 3.11..."
    sudo apt install -y python3.11 python3.11-venv python3-pip

    echo "🐘 Installing PostgreSQL..."
    sudo apt install -y postgresql postgresql-contrib
    
    # PostgreSQL 설정
    sudo -u postgres psql << EOF
CREATE USER meari WITH PASSWORD 'meari2024!';
CREATE DATABASE meari_db OWNER meari;
GRANT ALL PRIVILEGES ON DATABASE meari_db TO meari;
EOF

    echo "📊 Restoring database..."
    sudo -u postgres psql meari_db < ~/meari_db_dump.sql

    echo "🔧 Installing Nginx..."
    sudo apt install -y nginx

    echo "📂 Setting up backend..."
    tar -xzf meari-backend.tar.gz
    cd meari-backend

    # Python 가상환경
    python3.11 -m venv venv
    source venv/bin/activate

    # 의존성 설치
    pip install --upgrade pip
    pip install -r requirements-minimal.txt

    # .env 파일 이동 및 수정
    mv ../.env .
    
    # DATABASE_URL을 로컬 PostgreSQL로 변경
    sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql://meari:meari2024!@localhost/meari_db|' .env

    # BACKEND_URL을 EC2 IP로 설정
    echo "BACKEND_URL=http://$EC2_IP" >> .env

    echo "🚀 Installing PM2..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    sudo npm install -g pm2

    echo "🎯 Starting FastAPI with PM2..."
    pm2 start ecosystem.config.js
    pm2 save
    pm2 startup | tail -n 1 | sudo bash

    echo "🔧 Configuring Nginx..."
    sudo tee /etc/nginx/sites-available/meari << EOF
server {
    listen 80;
    server_name $EC2_IP;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

    # Nginx 활성화
    sudo ln -sf /etc/nginx/sites-available/meari /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx

    # 방화벽 설정
    sudo ufw allow 22
    sudo ufw allow 80
    sudo ufw allow 443
    sudo ufw allow 8000
    sudo ufw --force enable

    echo "✅ Deployment complete!"
    echo "📍 Server Info:"
    echo "   - API: http://$EC2_IP"
    echo "   - Docs: http://$EC2_IP/docs"
    echo "   - Database: PostgreSQL (local)"
    echo "   - Process Manager: PM2"
    echo "   - Web Server: Nginx"
ENDSSH

# 5. ecosystem.config.js 생성
cat << EOF > ecosystem.config.js
module.exports = {
  apps: [{
    name: 'meari-backend',
    script: 'venv/bin/uvicorn',
    args: 'app.main:app --host 0.0.0.0 --port 8000 --workers 2',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: 'logs/err.log',
    out_file: 'logs/out.log',
    log_file: 'logs/combined.log',
    time: true
  }]
};
EOF

# ecosystem.config.js 전송
scp -i $KEY_PATH ecosystem.config.js ubuntu@$EC2_IP:~/meari-backend/

# 6. 정리
rm meari-backend.tar.gz
rm ecosystem.config.js

echo "
====================================
🎉 배포 완료!
====================================

📋 다음 단계:

1. Google OAuth 설정 업데이트:
   - Redirect URI: http://$EC2_IP/auth/google/callback

2. 프론트엔드 환경변수 업데이트:
   - REACT_APP_API_URL=http://$EC2_IP

3. API 테스트:
   - http://$EC2_IP/docs

4. 서버 모니터링:
   ssh -i $KEY_PATH ubuntu@$EC2_IP
   pm2 status
   pm2 logs

5. DB 접속 (필요시):
   ssh -i $KEY_PATH ubuntu@$EC2_IP
   sudo -u postgres psql meari_db
"