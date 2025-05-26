from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/recommendations')
def get_recommendations():
    # Jalankan semua kode analisis kamu di sini (atau sebelumnya)
    rekomendasi = generate_recommendations(coin_metrics)
    return jsonify(rekomendasi)

if __name__ == '__main__':
    app.run(debug=True)