from flask import Flask, request, jsonify
import random

app = Flask(__name__)

EDGE_NODES = ["edge-chennai", "edge-bangalore", "edge-hyderabad"]

@app.route("/")
def home():
    return jsonify({"status": "Orchestrator online", "nodes": EDGE_NODES})

@app.route("/process", methods=["GET"])
def process():
    mode = request.args.get("mode", "dynamic")
    payload = request.args.get("payload", "100")
    selected_node = random.choice(EDGE_NODES)
    
    return jsonify({
        "status": "success",
        "mode": mode,
        "payload_size": payload,
        "routed_edge_node": selected_node
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)