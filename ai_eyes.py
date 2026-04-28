import cv2
import customtkinter as ctk
from PIL import Image, ImageTk
import time
import json
import firebase_admin
from firebase_admin import credentials, db
from pyzbar import pyzbar
from datetime import datetime

# --- ☁️ CLOUD CONFIGURATION ---
try:
    # 1. Initialize the Bridge using your secret key
    cred = credentials.Certificate("serviceAccountKey.json")
    
    # 2. Connect to your specific Singapore server
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://issac-ai-enterprise-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })
    print("SUCCESS: Issac AI Enterprise Cloud Online")
except Exception as e:
    print(f"CLOUD ERROR: {e}. Check if serviceAccountKey.json exists.")

class AITotalVision(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ISSAC AI | GLOBAL ENTERPRISE VISION v1.7")
        self.geometry("1100x650")

        self.asset_count = 0
        self.last_logged_time = 0
        self.is_running = True
        self.frame_count = 0

        # --- UI LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=280)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="● CLOUD CONNECTED", text_color="green")
        self.status_label.pack(pady=20)

        self.count_var = ctk.StringVar(value="Cloud Assets: 0")
        ctk.CTkLabel(self.sidebar, textvariable=self.count_var, font=("Arial", 24, "bold")).pack(pady=50)

        self.barcode_var = ctk.StringVar(value="Serial: Scanning...")
        ctk.CTkLabel(self.sidebar, textvariable=self.barcode_var, font=("Arial", 12)).pack(pady=10)

        # Added a history box to see live syncs
        self.history_box = ctk.CTkTextbox(self.sidebar, width=240, height=200)
        self.history_box.pack(pady=20, padx=10)
        self.history_box.insert("0.0", "Cloud Sync History:\n")

        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.grid(row=0, column=1)

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.update_loop()

    def sync_to_firebase(self, label, serial="N/A"):
        """Sends data to the Google Cloud Database"""
        try:
            ref = db.reference('inventory_logs')
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            ref.push({
                'item_type': label,
                'serial_number': serial,
                'timestamp': timestamp,
                'location': 'Dimapur_Hub_01'
            })
            
            # Update the UI History Box
            self.history_box.insert("end", f"[{timestamp[-8:]}] Sync: {label}\n")
            self.history_box.see("end")
            print(f"✅ Cloud Synced: {label}")
        except Exception as e:
            print(f"❌ Sync Failed: {e}")

    def update_loop(self):
        if not self.is_running: return

        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1
            current_serial = "Scanning..."
            
            # 1. BARCODE DETECTION
            barcodes = pyzbar.decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode("utf-8")
                current_serial = barcode_data
                self.barcode_var.set(f"Serial: {barcode_data}")
                
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame, "BARCODE", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # 2. SHAPE DETECTION & CLOUD SYNC (Every 5 seconds to avoid spamming)
            if self.frame_count % 3 == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150) 
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > 6000:
                        x, y, w, h = cv2.boundingRect(cnt)
                        ar = float(w)/h
                        label = None
                        if 2.5 < ar < 4.8: label = "RAM"
                        elif 0.8 < ar < 1.3: label = "CPU"
                        elif 1.3 <= ar <= 2.3: label = "ACCESSORY"

                        if label:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            
                            # Log to Cloud every 4 seconds if object is steady
                            if (time.time() - self.last_logged_time > 4):
                                self.asset_count += 1
                                self.last_logged_time = time.time()
                                self.count_var.set(f"Cloud Assets: {self.asset_count}")
                                
                                # TRIGGER CLOUD PUSH
                                self.sync_to_firebase(label, current_serial)

            # UI Update
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(720, 480))
            self.video_label.configure(image=img_tk)

        self.after(1, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = AITotalVision()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()