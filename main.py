import requests
import pandas as pd
from textblob import TextBlob
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
# import matplotlib.pyplot as plt # Plotting tidak bisa langsung ditampilkan di terminal HTML, pertimbangkan alternatif
from flask import Flask, jsonify, request
from flask_cors import CORS # Untuk mengizinkan permintaan dari domain berbeda (localhost frontend ke localhost backend)

# --- [ SEMUA FUNGSI ANDA YANG SUDAH ADA: get_active_cryptocurrencies, get_cryptopanic_news, dll. ] ---
# Pastikan fungsi-fungsi ini ada di sini. Saya akan meringkasnya untuk brevity.

# 1. SISTEM PENGAMBILAN COIN AKTUAL
def get_active_cryptocurrencies():
    active_coins = set()
    try:
        cg_url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=3000" # Mungkin kurangi jumlahnya untuk pengujian awal
        response = requests.get(cg_url, timeout=10) # Tambahkan timeout
        response.raise_for_status()
        data = response.json()
        for coin in data:
            active_coins.add(coin['symbol'].upper())
    except Exception as e:
        print(f"Error CoinGecko: {e}")
    return active_coins

# 2. SISTEM PENGAMBILAN BERITA REAL-TIME DARI CRYPTOPANIC
def get_cryptopanic_news(api_key, filter_currencies=None, days=1):
    base_url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        'auth_token': api_key,
        'public': 'true',
        'kind': 'news',
        'filter': 'rising' if not filter_currencies else 'custom',
        'currencies': filter_currencies if filter_currencies else None
    }
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    all_news = []
    page = 1
    max_pages = 3 # Batasi jumlah halaman untuk menghindari request terlalu lama
    try:
        while True:
            if page > max_pages:
                print(f"CryptoPanic: Reached max pages ({max_pages})")
                break
            params['page'] = page
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data.get('results'):
                break
            news_added_this_page = False
            for news_item in data['results']:
                published_str = news_item.get('published_at', '')
                if not published_str: continue
                try:
                    published = datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    print(f"CryptoPanic: Invalid date format for {news_item.get('title')}")
                    continue

                if published >= start_date:
                    all_news.append(news_item)
                    news_added_this_page = True
                else: # Berita sudah terlalu lama, dan karena diurutkan berdasarkan tanggal, kita bisa berhenti
                    print("CryptoPanic: Reached news older than start_date, stopping.")
                    return all_news
            if not news_added_this_page and data.get('next') is None: # Tidak ada berita baru di halaman ini dan tidak ada halaman selanjutnya
                break
            page += 1
    except requests.exceptions.RequestException as e:
        print(f"Error CryptoPanic API: {e}")
    except Exception as e:
        print(f"Unexpected error in get_cryptopanic_news: {e}")
    return all_news


# 2b. SISTEM PENGAMBILAN BERITA REAL-TIME DARI COINMARKETCAP
def get_coinmarketcap_news(api_key, limit=5):
    base_url = "https://pro-api.coinmarketcap.com/v1/content/posts/top"
    headers = {'X-CMC_PRO_API_KEY': api_key}
    params = {'limit': limit}
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"Error CoinMarketCap API: {e}")
        return []

# 3. SISTEM ANALISIS SENTIMEN TERPADU DENGAN TREND DAN SUMBER
def analyze_news_sentiment(news_items_cryptopanic, news_items_cmc, active_coins):
    analysis_results = []
    coin_metrics = defaultdict(lambda: {'mentions': 0, 'sentiment_sum': 0, 'news_count': 0, 'sentiment_history': [], 'source_sentiment': defaultdict(float)}) # float untuk sentimen

    # Analisis berita dari CryptoPanic
    for item in news_items_cryptopanic:
        title = item.get('title', '')
        # 'body' mungkin tidak selalu ada atau bisa sangat panjang, pertimbangkan untuk tidak menggunakannya atau membatasinya
        # body = item.get('body', '')
        votes = item.get('votes', {})
        source = item.get('source', {}).get('name', 'Unknown Source')
        mentioned_coins = set()

        # Identifikasi koin yang disebutkan
        if item.get('currencies'):
            for curr in item['currencies']:
                coin_symbol = curr.get('code', '').upper()
                if coin_symbol in active_coins:
                    mentioned_coins.add(coin_symbol)
        else: # Fallback ke pencarian di judul jika 'currencies' tidak ada
            for coin in active_coins:
                if f" {coin} " in f" {title.upper()} " or title.upper().startswith(coin + " ") or title.upper().endswith(" " + coin):
                     mentioned_coins.add(coin)

        text_to_analyze = title # Fokus analisis sentimen pada judul
        blob = TextBlob(text_to_analyze)
        polarity = blob.sentiment.polarity

        if votes:
            positive = votes.get('positive', 0)
            negative = votes.get('negative', 0)
            important = votes.get('important', 0)
            vote_impact = (positive - negative) * 0.05 + important * 0.02 # Kurangi bobot vote
            polarity = max(-1, min(1, polarity + vote_impact))

        for coin in mentioned_coins:
            coin_metrics[coin]['mentions'] += 1
            coin_metrics[coin]['sentiment_sum'] += polarity
            coin_metrics[coin]['news_count'] += 1
            coin_metrics[coin]['sentiment_history'].append(polarity)
            coin_metrics[coin]['source_sentiment'][source] += polarity

        analysis_results.append({
            'title': title,
            'url': item.get('url'),
            'published': item.get('published_at'),
            'coins': list(mentioned_coins),
            'sentiment': polarity,
            'importance': votes.get('important', 0) if votes else 0,
            'source': source,
            'api_source': 'CryptoPanic'
        })

    # Analisis berita dari CoinMarketCap (struktur field mungkin perlu disesuaikan berdasarkan respons API aktual)
    for item in news_items_cmc:
        title = item.get('meta', {}).get('title', '')
        # content = item.get('content', '') # Mungkin tidak perlu atau terlalu panjang
        source = item.get('source', {}).get('name', 'CoinMarketCap')
        published_at = item.get('meta',{}).get('releasedAt') # Sesuaikan dengan field API yang benar
        mentioned_coins_cmc = set()

        if isinstance(item.get('coins'), list): # Struktur dari CoinMarketCap API v1/content/posts/top
            for currency_info in item['coins']:
                coin_symbol_cmc = currency_info.get('slug','').upper() # atau 'symbol' jika ada, slug mungkin lebih unik
                # Perlu mapping slug ke symbol jika berbeda, atau pastikan active_coins juga bisa handle slugs
                # Untuk sementara, kita asumsikan slug bisa cocok dengan symbol di active_coins atau active_coins mengandung slug
                # Ini mungkin memerlukan penyesuaian lebih lanjut tergantung data CoinGecko vs CoinMarketCap
                # Contoh sederhana: coba cari symbol jika ada, jika tidak gunakan slug
                simple_symbol_guess = currency_info.get('symbol', coin_symbol_cmc).upper()
                if simple_symbol_guess in active_coins:
                     mentioned_coins_cmc.add(simple_symbol_guess)
                elif coin_symbol_cmc in active_coins: # fallback ke slug
                     mentioned_coins_cmc.add(coin_symbol_cmc)


        text_to_analyze_cmc = title
        blob_cmc = TextBlob(text_to_analyze_cmc)
        polarity_cmc = blob_cmc.sentiment.polarity

        for coin in mentioned_coins_cmc:
            coin_metrics[coin]['mentions'] += 1
            coin_metrics[coin]['sentiment_sum'] += polarity_cmc
            coin_metrics[coin]['news_count'] += 1
            coin_metrics[coin]['sentiment_history'].append(polarity_cmc)
            coin_metrics[coin]['source_sentiment'][source] += polarity_cmc

        analysis_results.append({
            'title': title,
            'url': item.get('meta',{}).get('url'), # Sesuaikan
            'published': published_at,
            'coins': list(mentioned_coins_cmc),
            'sentiment': polarity_cmc,
            'importance': 0,
            'source': source,
            'api_source': 'CoinMarketCap'
        })

    # Hitung trend sentimen
    for coin, metrics in coin_metrics.items():
        history_length = len(metrics['sentiment_history'])
        if history_length >= 2: # Cukup dengan 2 poin untuk trend sederhana
            # Trend sederhana: sentimen berita terbaru vs rata-rata sebelumnya
            trend = metrics['sentiment_history'][-1] - (np.mean(metrics['sentiment_history'][:-1]) if history_length > 1 else metrics['sentiment_history'][-1])
            coin_metrics[coin]['sentiment_trend'] = trend
        else:
            coin_metrics[coin]['sentiment_trend'] = 0.0

    return analysis_results, coin_metrics


# 4. SISTEM REKOMENDASI MATEMATIS DENGAN SKOR TREND DAN KONSISTENSI
def generate_recommendations(coin_metrics):
    recommendations = []
    for coin, metrics in coin_metrics.items():
        if metrics['news_count'] == 0: continue # Lewati koin tanpa berita

        avg_sentiment = metrics['sentiment_sum'] / metrics['news_count']
        popularity = metrics['mentions'] # Gunakan mentions sebagai proxy popularitas
        trend_score = metrics.get('sentiment_trend', 0.0)

        # Konsistensi: std deviasi, tapi normalisasi agar skor lebih tinggi lebih baik
        # Jika hanya 1 berita, std deviasi adalah 0, anggap konsisten
        sentiment_std = np.std(metrics['sentiment_history']) if len(metrics['sentiment_history']) > 1 else 0.0
        consistency_score = 1.0 / (1.0 + sentiment_std) # Nilai antara (0, 1], lebih tinggi lebih baik

        # Bobot yang disesuaikan
        # Prioritaskan sentimen rata-rata dan tren, lalu popularitas dan konsistensi
        score = (avg_sentiment * 0.4) + (trend_score * 0.3) + (popularity * 0.15 / (metrics['news_count'] if metrics['news_count'] > 0 else 1)) + (consistency_score * 0.15)

        recommendations.append({
            'coin': coin,
            'score': score,
            'avg_sentiment': avg_sentiment,
            'mentions': metrics['mentions'],
            'news_count': metrics['news_count'],
            'sentiment_trend': trend_score,
            'sentiment_consistency_score': consistency_score, # Menggunakan skor yang sudah dinormalisasi
            # 'sentiment_std_dev': sentiment_std # Opsional, untuk debugging
        })
    return sorted(recommendations, key=lambda x: x['score'], reverse=True)

# Modifikasi fungsi display untuk mengembalikan data, bukan print
def format_analysis_for_frontend(analysis_results, recommendations, coin_metrics):
    output = {"news": [], "recommendations": []}

    # Format berita
    for news in analysis_results[:10]: # Batasi jumlah berita yang dikirim ke frontend
        coins = ', '.join(news['coins']) if news['coins'] else "N/A"
        sentiment_label = "🟢 Positif" if news['sentiment'] > 0.1 else "🔴 Negatif" if news['sentiment'] < -0.1 else "⚪ Netral"
        output["news"].append(
            f"📌 [{news['api_source']}] {news['title']}\n"
            f"   ⏱️ {news.get('published','N/A')} | Sumber: {news.get('source','N/A')} | Sentimen: {sentiment_label} ({news['sentiment']:.2f})\n"
            f"   💰 Coin: {coins}\n"
            f"   🔗 {news.get('url', 'N/A')}"
        )

    # Format rekomendasi
    for idx, rec in enumerate(recommendations[:5], 1): # Batasi jumlah rekomendasi
        trend_indicator = "📈 Naik" if rec['sentiment_trend'] > 0.05 else "📉 Turun" if rec['sentiment_trend'] < -0.05 else "➡️ Stabil"
        recommendation_text = (
            f"{idx}. {rec['coin']}:\n"
            f"   - Skor: {rec['score']:.2f}\n"
            f"   - Sentimen Rata-rata: {rec['avg_sentiment']:.2f}\n"
            f"   - Trend Sentimen: {trend_indicator} ({rec['sentiment_trend']:.2f})\n"
            # f"   - Konsistensi (Skor): {rec['sentiment_consistency_score']:.2f}\n"
            f"   - Mention: {rec['mentions']} dalam {rec['news_count']} berita"
        )
        # Info sentimen per sumber bisa ditambahkan jika dirasa perlu, tapi bisa membuat output panjang
        # sources_summary = []
        # if rec['coin'] in coin_metrics:
        #     for source, sentiment_val in sorted(coin_metrics[rec['coin']]['source_sentiment'].items(), key=lambda item: item[1], reverse=True)[:2]:
        #         sources_summary.append(f"{source}: {sentiment_val:.2f}")
        # if sources_summary:
        #     recommendation_text += f"\n   - Sentimen Sumber Top: {'; '.join(sources_summary)}"
        output["recommendations"].append(recommendation_text)

    # Grafik tidak bisa dikirim langsung. Bisa mengirim data untuk grafik jika frontend bisa merendernya,
    # atau simpan sebagai gambar dan kirim URL (lebih kompleks). Untuk sekarang, kita hilangkan plot.
    # Contoh: mengirim data history untuk koin teratas jika diinginkan
    # if recommendations and recommendations[0]['coin'] in coin_metrics:
    # output['top_coin_sentiment_history'] = {
    # 'coin': recommendations[0]['coin'],
    # 'history': coin_metrics[recommendations[0]['coin']]['sentiment_history']
    # }

    return output

app = Flask(__name__)
CORS(app) # Ini akan mengizinkan semua origin. Untuk produksi, konfigurasikan lebih spesifik.

CRYPTO_PANIC_API_KEY = "cf627eaedcfb3c60f48d100e3ebeaba45eb6ef38" # Ambil dari environment variable idealnya
COINMARKETCAP_API_KEY = "8882b616-d602-4227-ac36-8af1cbd5f244" # Ambil dari environment variable idealnya

@app.route('/analyze_crypto', methods=['GET'])
def analyze_crypto_endpoint():
    print("🔄 Mengambil daftar coin aktif...")
    active_coins = get_active_cryptocurrencies()
    if not active_coins:
        return jsonify({"error": "Tidak bisa mengambil daftar koin aktif."}), 500
    print(f"✅ Ditemukan {len(active_coins)} coin aktif di pasar")

    print("\n📡 Mengambil berita terkini dari CryptoPanic (24 jam terakhir)...")
    # Ambil dari query param jika ada, jika tidak default ke 1 hari
    days_to_fetch = request.args.get('days', default=1, type=int)
    news_items_cryptopanic = get_cryptopanic_news(CRYPTO_PANIC_API_KEY, days=days_to_fetch)
    print(f"📰 Ditemukan {len(news_items_cryptopanic)} berita dari CryptoPanic")

    print("\n📰 Mengambil berita terkini dari CoinMarketCap...")
    cmc_limit = request.args.get('cmc_limit', default=20, type=int) # Ambil 20 berita terbaru CMC
    news_items_cmc = get_coinmarketcap_news(COINMARKETCAP_API_KEY, limit=cmc_limit)
    print(f"📰 Ditemukan {len(news_items_cmc)} berita dari CoinMarketCap")

    if not news_items_cryptopanic and not news_items_cmc:
        return jsonify({"error": "Tidak ada berita yang bisa diambil dari kedua sumber."}), 500

    print("\n🧠 Menganalisis sentimen dan metrik coin dari kedua sumber...")
    analysis_results, coin_metrics = analyze_news_sentiment(news_items_cryptopanic, news_items_cmc, active_coins)

    if not coin_metrics: # Jika tidak ada koin yang teridentifikasi dari berita
        formatted_data = format_analysis_for_frontend(analysis_results, [], {}) # Kirim berita saja
        formatted_data["message"] = "Analisis sentimen berita selesai, namun tidak ada koin spesifik yang teridentifikasi dalam berita untuk dibuatkan rekomendasi."
        return jsonify(formatted_data)


    print("\n📈 Menghasilkan rekomendasi...")
    recommendations = generate_recommendations(coin_metrics)

    # Menggunakan fungsi format baru
    formatted_data = format_analysis_for_frontend(analysis_results, recommendations, coin_metrics)
    return jsonify(formatted_data)

if __name__ == "__main__":
    # Jalankan server Flask. Port 5001 agar tidak bentrok dengan port 5000 di JS awal Anda.
    app.run(debug=True, port=5001)
