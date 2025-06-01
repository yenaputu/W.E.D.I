import os
import requests
import gradio as gr
from dotenv import load_dotenv

# Untuk local debug: coba load dari .env
load_dotenv()

# Ambil API Key dari environment (gunakan Secrets di Hugging Face Settings)
API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

# Debug: cetak status API Key (untuk development, hapus sebelum produksi)
print("[DEBUG] API_KEY:", "Terdeteksi âœ…" if API_KEY else "Tidak Ditemukan âŒ")

# Fungsi untuk mengambil berita crypto dari CryptoPanic
def get_crypto_news():
    if not API_KEY:
        return "âŒ API key tidak ditemukan. Tambahkan di Settings > Secrets."

    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={API_KEY}&public=true"
    try:
        response = requests.get(url)
        data = response.json()
        if "results" in data:
            headlines = [item["title"] for item in data["results"][:5]]
            return "\n\n".join(f"{i+1}. {title}" for i, title in enumerate(headlines))
        else:
            return "âŒ Gagal mengambil berita dari API."
    except Exception as e:
        return f"âŒ Error saat request: {str(e)}"

# Fungsi utama yang dipanggil Gradio
def crypto_analyzer(user_input):
    news_summary = get_crypto_news()
    return f"ðŸ“° Berita Crypto Terkini:\n\n{news_summary}\n\nðŸ” Masukanmu: {user_input}"

# Interface Gradio
iface = gr.Interface(
    fn=crypto_analyzer,
    inputs=gr.Textbox(lines=2, placeholder="Apa yang ingin kamu ketahui?"),
    outputs="text",
    title="Crypto Market Analyzer",
    description="AI sederhana untuk menampilkan berita crypto terbaru dan menganalisis input kamu (tahap awal)."
)

# Untuk Hugging Face Spaces
if __name__ == "__main__":
    iface.launch()