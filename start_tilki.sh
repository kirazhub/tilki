#!/bin/bash
# Tilki Kripto Ajanı - Başlatma Scripti

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║          🦊 TİLKİ — Kripto Simülasyon Ajanı     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Python kontrolü
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 bulunamadı! Lütfen Python 3.9+ yükleyin."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python: $PYTHON_VERSION"

# Virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment oluşturuluyor..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "✅ Sanal ortam aktif"

# Bağımlılıklar
echo "📦 Bağımlılıklar kontrol ediliyor..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Bağımlılıklar yüklü"

# Mod seç
echo ""
echo "Hangi modu başlatmak istiyorsunuz?"
echo "  1) 🖥️  Dashboard (Streamlit)"
echo "  2) 🤖  Ajan (Arka planda çalışan loop)"
echo "  3) 🚀  Her ikisi (Ajan + Dashboard)"
echo ""
read -p "Seçim (1/2/3) [varsayılan: 1]: " SECIM
SECIM=${SECIM:-1}

case $SECIM in
    1)
        echo ""
        echo "🌐 Dashboard başlatılıyor: http://localhost:8501"
        echo "   Durdurmak için Ctrl+C"
        streamlit run tilki_dashboard.py \
            --server.port=8501 \
            --server.address=localhost \
            --theme.base=dark \
            --theme.primaryColor="#FF8C00" \
            --theme.backgroundColor="#0E1117" \
            --theme.secondaryBackgroundColor="#1E2130" \
            --theme.textColor="#FAFAFA"
        ;;
    2)
        echo ""
        echo "🤖 Tilki ajanı başlatılıyor..."
        echo "   Durdurmak için Ctrl+C"
        python3 tilki_main.py
        ;;
    3)
        echo ""
        echo "🚀 Ajan + Dashboard başlatılıyor..."
        # Ajanı arka planda çalıştır
        python3 tilki_main.py &
        AJAN_PID=$!
        echo "✅ Ajan başlatıldı (PID: $AJAN_PID)"
        echo "🌐 Dashboard: http://localhost:8501"
        echo ""

        # Dashboard'ı ön planda başlat
        streamlit run tilki_dashboard.py \
            --server.port=8501 \
            --server.address=localhost \
            --theme.base=dark \
            --theme.primaryColor="#FF8C00" \
            --theme.backgroundColor="#0E1117" \
            --theme.secondaryBackgroundColor="#1E2130" \
            --theme.textColor="#FAFAFA"

        # Dashboard durduğunda ajanı da durdur
        echo "Dashboard durdu. Ajan durduruluyor (PID: $AJAN_PID)..."
        kill $AJAN_PID 2>/dev/null || true
        ;;
    *)
        echo "❌ Geçersiz seçim"
        exit 1
        ;;
esac
