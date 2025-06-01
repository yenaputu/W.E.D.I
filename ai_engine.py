# crypto_ai_analyzer/ai_engine.py

def summarize_market(price_data, news_data):
    # Ini dummy. Kamu bisa ganti dengan LLM call nanti.
    coin = list(price_data.keys())[0]
    price = price_data[coin]['usd']
    news_count = len(news_data.get("results", []))

    return (
        f"Harga {coin.capitalize()}: ${price}\n"
        f"Jumlah berita terbaru: {news_count}\n"
        f"Pasar sedang {'positif' if news_count > 5 else 'tenang'}."
    )