webhook_urls = []  # Webhook URL'lerini saklamak için basit bir liste

@app.route('/add-webhook', methods=['POST'])
def add_webhook():
    url = request.json.get('url')
    if url:
        webhook_urls.append(url)
        return jsonify({'message': 'Webhook URL added successfully!'}), 200
    return jsonify({'message': 'Invalid URL'}), 400
