import requests
import pandas as pd
from textblob import TextBlob
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt  # Import library untuk plotting

# 1. SISTEM PENGAMBILAN COIN AKTUAL
def get_active_cryptocurrencies():
    """Mengambil daftar coin aktif dari CoinGecko (Top 3000 coins)"""
    active_coins = set()
    try:
        cg_url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=3000"
        response = requests.get(cg_url)
        data = response.json()
        for coin in data:
            active_coins.add(coin['symbol'].upper())
    except Exception as e:
        print(f"Error CoinGecko: {e}")
    return active_coins

# 2. SISTEM PENGAMBILAN BERITA REAL-TIME DARI CRYPTOPANIC
def get_cryptopanic_news(api_key, filter_currencies=None, days=1):
    """Mengambil berita terkini dari CryptoPanic"""
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

    while True:
        params['page'] = page
        response = requests.get(base_url, params=params)
        data = response.json()

        if not data.get('results'):
            break

        for news in data['results']:
            published = datetime.strptime(news['published_at'], "%Y-%m-%dT%H:%M:%SZ")
            if published >= start_date:
                all_news.append(news)
            else:
                return all_news
        page += 1
        if page > 5:
            break

    return all_news

# 2b. SISTEM PENGAMBILAN BERITA REAL-TIME DARI COINMARKETCAP
def get_coinmarketcap_news(api_key, limit=5):
    """Mengambil berita terkini dari CoinMarketCap menggunakan endpoint /v1/content/posts/top"""
    base_url = "https://pro-api.coinmarketcap.com/v1/content/posts/top"
    headers = {
        'X-CMC_PRO_API_KEY': api_key
    }
    params = {
        'limit': limit
    }
    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"Error CoinMarketCap API: {e}")
        return []

# 3. SISTEM ANALISIS SENTIMEN TERPADU DENGAN TREND DAN SUMBER
def analyze_news_sentiment(news_items_cryptopanic, news_items_cmc, active_coins):
    """Analisis sentimen dari CryptoPanic dan CoinMarketCap"""
    analysis_results = []
    coin_metrics = defaultdict(lambda: {'mentions': 0, 'sentiment_sum': 0, 'news_count': 0, 'sentiment_history': [], 'source_sentiment': defaultdict(int)})

    # Analisis berita dari CryptoPanic
    for item in news_items_cryptopanic:
        title = item.get('title', '')
        body = item.get('body', '')
        votes = item.get('votes', {})
        source = item.get('source', {}).get('name', 'Unknown Source')

        mentioned_coins = set()
        for coin in active_coins:
            if f" {coin} " in f" {title.upper()} " or (body and f" {coin} " in f" {body.upper()} "):
                mentioned_coins.add(coin)

        text = f"{title}. {body}"
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if votes:
            positive = votes.get('positive', 0)
            negative = votes.get('negative', 0)
            important = votes.get('important', 0)
            vote_impact = (positive - negative) * 0.1 + important * 0.05
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

    # Analisis berita dari CoinMarketCap
    for item in news_items_cmc:
        title = item.get('title', '') # Perkiraan nama field
        content = item.get('content', '') # Perkiraan nama field
        source = item.get('source', {}).get('name', 'CoinMarketCap') # Perkiraan struktur
        published_at = item.get('created_at') # Perkiraan nama field

        mentioned_coins = set()
        if isinstance(item.get('currencies'), list): # Perkiraan struktur
            for currency in item['currencies']:
                mentioned_coins.add(currency.get('symbol'))

        text = f"{title}. {content}"
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        for coin in mentioned_coins:
            if coin in active_coins:
                coin_metrics[coin]['mentions'] += 1
                coin_metrics[coin]['sentiment_sum'] += polarity
                coin_metrics[coin]['news_count'] += 1
                coin_metrics[coin]['sentiment_history'].append(polarity)
                coin_metrics[coin]['source_sentiment'][source] += polarity

        analysis_results.append({
            'title': title,
            'url': item.get('url'), # Perkiraan nama field
            'published': published_at,
            'coins': list(mentioned_coins),
            'sentiment': polarity,
            'importance': 0, # CoinMarketCap tidak memiliki voting seperti CryptoPanic
            'source': source,
            'api_source': 'CoinMarketCap'
        })

    # Hitung trend sentimen
    for coin, metrics in coin_metrics.items():
        history_length = len(metrics['sentiment_history'])
        if history_length >= 3:
            trend = np.mean(metrics['sentiment_history'][-3:]) - np.mean(metrics['sentiment_history'][:max(0, history_length - 3)])
            coin_metrics[coin]['sentiment_trend'] = trend
        else:
            coin_metrics[coin]['sentiment_trend'] = 0

    return analysis_results, coin_metrics

# 4. SISTEM REKOMENDASI MATEMATIS DENGAN SKOR TREND DAN KONSISTENSI
def generate_recommendations(coin_metrics):
    """Generate rekomendasi berbasis statistik dengan mempertimbangkan trend dan konsistensi"""
    recommendations = []

    for coin, metrics in coin_metrics.items():
        avg_sentiment = metrics['sentiment_sum'] / metrics['news_count'] if metrics['news_count'] > 0 else 0
        popularity = metrics['mentions']
        trend_score = metrics.get('sentiment_trend', 0) * 0.5  # Bobot trend
        # Ukur konsistensi sentimen (standar deviasi rendah = konsisten)
        sentiment_std = np.std(metrics['sentiment_history']) if metrics['sentiment_history'] else 0
        consistency_score = 1 - sentiment_std  # Semakin rendah std, semakin tinggi skor konsistensi

        # Pemberian bobot yang disesuaikan
        score = (avg_sentiment * 0.4) + (popularity * 0.3) + (trend_score * 0.2) + (consistency_score * 0.1)

        recommendations.append({
            'coin': coin,
            'score': score,
            'avg_sentiment': avg_sentiment,
            'mentions': metrics['mentions'],
            'news_count': metrics['news_count'],
            'sentiment_trend': metrics.get('sentiment_trend', 0),
            'sentiment_consistency': consistency_score,
        })

    return sorted(recommendations, key=lambda x: x['score'], reverse=True)

# 5. TAMPILAN HASIL REAL-TIME YANG DIPERBARUI DENGAN GRAFIK
def display_realtime_analysis(analysis_results, recommendations, coin_metrics):
    """Menampilkan hasil analisis dengan visual jelas termasuk trend, sumber, dan grafik"""
    print(f"\n📊 HASIL ANALISIS TERKINI ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("="*60)

    print("\n🔥 BERITA TERKINI:")
    for news in analysis_results[:5]: # Tampilkan lebih banyak berita
        coins = ', '.join(news['coins']) if news['coins'] else "Tidak ada coin spesifik"
        sentiment = "🟢 Positif" if news['sentiment'] > 0.1 else "🔴 Negatif" if news['sentiment'] < -0.1 else "⚪ Netral"
        print(f"\n📌 [{news['api_source']}] {news['title']}")
        print(f"⏱️ {news['published']} | Sumber: {news['source']} | Sentimen: {sentiment} ({news['sentiment']:.2f})")
        print(f"💰 Coin: {coins}")
        print(f"🔗 {news['url']}")

    print("\n🏆 REKOMENDASI COIN TERATAS:")
    for idx, rec in enumerate(recommendations[:5], 1):
        trend_indicator = "📈 Naik" if rec['sentiment_trend'] > 0.1 else "📉 Turun" if rec['sentiment_trend'] < -0.1 else "➡️ Stabil"
        print(f"{idx}. {rec['coin']}:")
        print(f"   - Skor: {rec['score']:.2f}")
        print(f"   - Sentimen Rata-rata: {rec['avg_sentiment']:.2f}")
        print(f"   - Trend Sentimen (3 berita terakhir): {trend_indicator} ({rec['sentiment_trend']:.2f})")
        print(f"   - Konsistensi Sentimen: {(rec['sentiment_consistency'] * 100):.2f}%")
        print(f"   - Jumlah Mention: {rec['mentions']} dalam {rec['news_count']} berita")
        print("   - Sentimen per Sumber:")
        for source, sentiment in sorted(coin_metrics[rec['coin']]['source_sentiment'].items(), key=lambda item: item[1], reverse=True)[:3]:
            sentiment_label = "Positif" if sentiment > 0 else "Negatif" if sentiment < 0 else "Netral"
            print(f"     - {source}: {sentiment_label} ({sentiment:.2f})")

        if rec['coin'] in coin_metrics and coin_metrics[rec['coin']]['sentiment_history']:
            plt.figure(figsize=(10, 4))
            plt.plot(coin_metrics[rec['coin']]['sentiment_history'])
            plt.title(f"Trend Sentimen {rec['coin']}")
            plt.xlabel("Berita")
            plt.ylabel("Sentimen")
            plt.grid(True)
            plt.show()
        else:
            print("   - Tidak cukup data untuk membuat grafik sentimen.\n")
        print("\n")

# MAIN PROGRAM
if __name__ == "__main__":
    CRYPTO_PANIC_API_KEY = "cf627eaedcfb3c60f48d100e3ebeaba45eb6ef38"
    COINMARKETCAP_API_KEY = "8882b616-d602-4227-ac36-8af1cbd5f244"

    print("🔄 Mengambil daftar coin aktif...")
    active_coins = get_active_cryptocurrencies()
    print(f"✅ Ditemukan {len(active_coins)} coin aktif di pasar")

    print("\n📡 Mengambil berita terkini dari CryptoPanic (24 jam terakhir)...")
    news_items_cryptopanic = get_cryptopanic_news(CRYPTO_PANIC_API_KEY, days=1)
    print(f"📰 Ditemukan {len(news_items_cryptopanic)} berita dari CryptoPanic")

    print("\n📰 Mengambil berita terkini dari CoinMarketCap...")
    news_items_cmc = get_coinmarketcap_news(COINMARKETCAP_API_KEY)
    print(f"📰 Ditemukan {len(news_items_cmc)} berita dari CoinMarketCap")

    print("\n🧠 Menganalisis sentimen dan metrik coin dari kedua sumber...")
    analysis_results, coin_metrics = analyze_news_sentiment(news_items_cryptopanic, news_items_cmc, active_coins)

    print("\n📈 Menghasilkan rekomendasi...")
    recommendations = generate_recommendations(coin_metrics)

    display_realtime_analysis(analysis_results, recommendations, coin_metrics)
