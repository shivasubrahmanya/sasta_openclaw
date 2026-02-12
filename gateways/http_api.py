from flask import Flask, request, jsonify
from gateways.base import Gateway
import threading

class HttpGateway(Gateway):
    def __init__(self, port: int, on_message):
        super().__init__(on_message)
        self.port = port
        self.app = Flask(__name__)
        
        @self.app.route('/chat', methods=['POST'])
        def chat():
            data = request.json
            session_id = data.get('session_id')
            message = data.get('message')
            
            if not session_id or not message:
                return jsonify({"error": "Missing session_id or message"}), 400
            
            response = self.on_message(session_id, message)
            return jsonify({"response": response})

    def start(self):
        # Run Flask in a separate thread so it doesn't block other gateways
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print(f"HTTP Gateway started on port {self.port}")

    def _run(self):
        self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)

    def stop(self):
        # Flask doesn't have a clean stop method without extensions, 
        # but daemon thread will die when main process exits.
        pass
