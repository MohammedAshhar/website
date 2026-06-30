import http.server
import json
import os
import uuid
import mimetypes
from datetime import datetime
from urllib.parse import urlparse

PORT = 3000
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"patients": [], "bookings": [], "reports": [], "doctors": [], "tests": []}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def uid():
    return "-".join("".join(format(random.randint(0, 15), "x") for _ in range(4)) for _ in range(3))


import random


def seed():
    data = load_data()
    if not data["doctors"]:
        data["doctors"] = [
            {"doctor_id": uid(), "name": "Dr. M.A. Majid Adil", "speciality": "UROLOGIST",
             "qualifications": "MBBS, M.D, MDHM",
             "bio": "Dr. Majid Adil is a highly skilled and experienced urologist affiliated with Unicus Diagnostics. With a passion for providing exceptional patient care, Dr. Adil has gained a reputation for his expertise in diagnosing and treating various urological conditions."},
            {"doctor_id": uid(), "name": "Dr. Shahana Sarwar", "speciality": "MANAGING DIRECTOR",
             "qualifications": "MBBS, M.D, MDHM",
             "bio": "Dr. Shahana Sarwar is a highly accomplished individual serving as the Managing Director of Unicus Diagnostics. With her exceptional leadership skills and extensive expertise in the field of diagnostics, she has propelled Unicus Diagnostics to new heights of success and recognition."},
        ]
    if not data["tests"]:
        data["tests"] = [
            {"test_id": uid(), "name": "Creatinine Test", "price": 300,
             "description": "Measures creatinine levels to assess kidney function.", "category": "Pathology"},
            {"test_id": uid(), "name": "CBC Test", "price": 400,
             "description": "Complete Blood Count \u2014 evaluates overall health and detects disorders.", "category": "Pathology"},
            {"test_id": uid(), "name": "C Reactive Protein Test", "price": 500,
             "description": "Measures CRP levels to detect inflammation or infection.", "category": "Pathology"},
            {"test_id": uid(), "name": "Blood Sugar", "price": 200,
             "description": "Measures glucose levels in the blood for diabetes screening.", "category": "Pathology"},
        ]
    save_data(data)


seed()

BASE_DIR = os.path.dirname(__file__)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self.handle_api()
            return

        self.directory = BASE_DIR
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.handle_api()

    def handle_api(self):
        parsed = urlparse(self.path)
        path = parsed.path
        method = self.command
        data = load_data()

        def send(code, body):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def read_body():
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length).decode())

        try:
            # GET /api/doctors
            if path == "/api/doctors" and method == "GET":
                return send(200, data["doctors"])

            # GET /api/tests
            elif path == "/api/tests" and method == "GET":
                return send(200, data["tests"])

            # GET /api/patient/phone/{phone}
            elif path.startswith("/api/patient/phone/") and method == "GET":
                phone = path.split("/api/patient/phone/")[1]
                patient = next((p for p in data["patients"] if p["phone"] == phone), None)
                if not patient:
                    return send(404, {"error": "Patient not found"})
                return send(200, patient)

            # GET /api/patient/{id}
            elif path.startswith("/api/patient/") and method == "GET":
                pid = path.split("/api/patient/")[1]
                patient = next((p for p in data["patients"] if p["patient_id"] == pid), None)
                if not patient:
                    return send(404, {"error": "Patient not found"})
                return send(200, patient)

            # POST /api/patient/create
            elif path == "/api/patient/create" and method == "POST":
                body = read_body()
                existing = next((p for p in data["patients"] if p["phone"] == body["phone"]), None)
                if existing:
                    return send(200, existing)
                patient = {
                    "patient_id": uid(), "name": body["name"], "phone": body["phone"],
                    "address": body.get("address", ""), "created_at": datetime.utcnow().isoformat()
                }
                data["patients"].append(patient)
                save_data(data)
                return send(200, patient)

            # POST /api/booking/create
            elif path == "/api/booking/create" and method == "POST":
                body = read_body()
                patient = next((p for p in data["patients"] if p["phone"] == body["patient_phone"]), None)
                if not patient:
                    patient = {
                        "patient_id": uid(), "name": body["patient_name"],
                        "phone": body["patient_phone"], "address": body["collection_address"],
                        "created_at": datetime.utcnow().isoformat()
                    }
                    data["patients"].append(patient)
                booking = {
                    "booking_id": uid(), "patient_id": patient["patient_id"],
                    "patient_name": body["patient_name"], "patient_phone": body["patient_phone"],
                    "test_name": body["test_name"], "collection_address": body["collection_address"],
                    "status": "confirmed", "created_at": datetime.utcnow().isoformat()
                }
                data["bookings"].append(booking)
                report = {
                    "report_id": uid(), "booking_id": booking["booking_id"],
                    "patient_id": patient["patient_id"], "test_name": booking["test_name"],
                    "results": f"Test: {booking['test_name']}\nResult: Normal\nReference Range: As per clinical correlation\nRemarks: No significant abnormality detected.",
                    "generated_at": datetime.utcnow().isoformat()
                }
                data["reports"].append(report)
                save_data(data)
                return send(200, booking)

            # GET /api/booking/{id}
            elif path.startswith("/api/booking/") and method == "GET":
                bid = path.split("/api/booking/")[1]
                booking = next((b for b in data["bookings"] if b["booking_id"] == bid), None)
                if not booking:
                    return send(404, {"error": "Booking not found"})
                return send(200, booking)

            # GET /api/bookings/{phone}
            elif path.startswith("/api/bookings/") and method == "GET":
                phone = path.split("/api/bookings/")[1]
                bookings = [b for b in data["bookings"] if b["patient_phone"] == phone]
                return send(200, bookings)

            # POST /api/report/create
            elif path == "/api/report/create" and method == "POST":
                body = read_body()
                booking = next((b for b in data["bookings"] if b["booking_id"] == body["booking_id"]), None)
                if not booking:
                    return send(404, {"error": "Booking not found"})
                report = {
                    "report_id": uid(), "booking_id": body["booking_id"],
                    "patient_id": booking["patient_id"], "test_name": booking["test_name"],
                    "results": body["results"], "generated_at": datetime.utcnow().isoformat()
                }
                data["reports"].append(report)
                save_data(data)
                return send(200, report)

            # GET /api/report/{booking_id}
            elif path.startswith("/api/report/") and method == "GET":
                bid = path.split("/api/report/")[1]
                report = next((r for r in data["reports"] if r["booking_id"] == bid), None)
                if not report:
                    return send(404, {"error": "Report not found for this booking"})
                return send(200, report)

            # GET /api/gallery — list images in the images/ folder
            elif path == "/api/gallery" and method == "GET":
                img_dir = os.path.join(BASE_DIR, "images")
                exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
                files = []
                try:
                    for f in sorted(os.listdir(img_dir)):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in exts and f.lower().startswith("gallery"):
                            files.append("images/" + f)
                except OSError:
                    pass
                return send(200, files)

            # POST /api/seed
            elif path == "/api/seed" and method == "POST":
                seed()
                return send(200, {"status": "ok", "message": "Data seeded"})

            else:
                send(404, {"error": "API route not found"})

        except Exception as e:
            send(500, {"error": str(e)})

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} {args[2]}")


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Unicus Diagnostics server running at http://localhost:{PORT}")
    server.serve_forever()
