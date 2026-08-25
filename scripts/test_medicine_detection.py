from ultralytics import YOLO
import cv2

MODEL_PATH = "ai/medicine_detection/best.pt"

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Kamera laptop tidak bisa dibuka.")

print("Kamera aktif.")
print("Tekan Q untuk keluar.")

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Frame asli untuk YOLO
    results = model(frame, conf=0.5)

    # Hasil deteksi
    annotated_frame = results[0].plot()

    # Balik hanya untuk tampilan supaya wajah tidak mirror
    

    cv2.imshow(
    "SITARA - Medicine Detection",
    annotated_frame
)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()