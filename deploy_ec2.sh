#!/bin/bash

# EC2 배포 스크립트
# 사용법: ./deploy_ec2.sh <EC2_PUBLIC_IP>

if [ -z "$1" ]; then
    echo "Usage: ./deploy_ec2.sh <EC2_PUBLIC_IP>"
    exit 1
fi

EC2_IP=$1
KEY_PATH="~/Downloads/meari-backend-key.pem"

echo "🚀 Starting EC2 deployment to $EC2_IP"

# 1. SSH 키 권한 설정
chmod 400 $KEY_PATH

# 2. 필요한 파일들 압축
echo "📦 Preparing files..."
tar -czf meari-backend.tar.gz \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="*.pyc" \
    --exclude=".env" \
    .

# 3. EC2로 파일 전송
echo "📤 Uploading to EC2..."
scp -i $KEY_PATH meari-backend.tar.gz ubuntu@$EC2_IP:~/

# 4. .env 파일 별도 전송
echo "🔐 Uploading environment file..."
scp -i $KEY_PATH .env ubuntu@$EC2_IP:~/

# 5. 설치 스크립트 실행
echo "🔧 Running installation on EC2..."
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'ENDSSH'
    # 시스템 업데이트
    sudo apt update
    sudo apt upgrade -y

    # Python 3.11 설치
    sudo apt install -y python3.11 python3.11-venv python3-pip

    # PostgreSQL 클라이언트
    sudo apt install -y postgresql-client

    # Nginx 설치
    sudo apt install -y nginx

    # 압축 해제
    tar -xzf meari-backend.tar.gz
    cd meari-backend

    # 가상환경 생성 및 활성화
    python3.11 -m venv venv
    source venv/bin/activate

    # 의존성 설치 (minimal 버전)
    pip install --upgrade pip
    pip install -r requirements-minimal.txt

    # .env 파일 이동
    mv ../.env .

    # PM2 설치 (Node.js 필요)
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    sudo npm install -g pm2

    # PM2로 FastAPI 실행
    pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name meari-backend
    pm2 save
    pm2 startup | tail -n 1 | sudo bash

    # Nginx 설정
    sudo tee /etc/nginx/sites-available/meari << EOF
server {
    listen 80;
    server_name _;

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
    }
}
EOF

    # Nginx 활성화
    sudo ln -sf /etc/nginx/sites-available/meari /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx

    echo "✅ Deployment complete!"
    echo "📍 API available at: http://$EC2_IP"
    echo "📍 Docs available at: http://$EC2_IP/docs"
ENDSSH

# 6. 정리
rm meari-backend.tar.gz

echo "🎉 Deployment finished!"
echo "Next steps:"
echo "1. Update Google OAuth redirect URI to: http://$EC2_IP/auth/google/callback"
echo "2. Update frontend .env with: REACT_APP_API_URL=http://$EC2_IP"
echo "3. Test the API at: http://$EC2_IP/docs"