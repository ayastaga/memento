import cv2
import numpy as np
import time
import os
from insightface.app import FaceAnalysis
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class LiveFaceRecognitionMongo:
    def __init__(self, user_id=None, similarity_threshold=0.3):
        self.user_id = user_id
        self.similarity_threshold = similarity_threshold
        self.known_faces = {}

        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.people = self.db["people"]

        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=(320, 320))

    def load_embeddings(self):
        self.known_faces.clear()

        for p in self.people.find({
            "user_id": self.user_id,
            "embedding": {"$exists": True}
        }):
            self.known_faces[str(p["_id"])] = {
                "name": p["name"],
                "relation": p.get("relation", ""),
                "summary": p.get("summary", ""),
                "embedding": np.array(p["embedding"], dtype=np.float32)
            }

        print(f"Loaded {len(self.known_faces)} faces")

    @staticmethod
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def recognize(self, emb):
        best, score = None, 0.0
        for p in self.known_faces.values():
            s = self.cosine_similarity(emb, p["embedding"])
            if s > score:
                score = s
                best = p

        if best and score >= self.similarity_threshold:
            return best["name"], best["relation"], best["summary"]

        return None, None, None

    # ---------- Glass HUD ----------

    def draw_glass_hud(self, frame, x, y, w, h, radius=18):
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0:
            return

        # Blur background
        blurred = cv2.GaussianBlur(roi, (31, 31), 0)

        # Darker black tint
        dark = np.zeros_like(roi)
        dark[:] = (0, 0, 0)

        glass = cv2.addWeighted(blurred, 0.6, dark, 0.4, 0)

        # Rounded mask
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask, (radius, 0), (w-radius, h), 255, -1)
        cv2.rectangle(mask, (0, radius), (w, h-radius), 255, -1)
        cv2.circle(mask, (radius, radius), radius, 255, -1)
        cv2.circle(mask, (w-radius, radius), radius, 255, -1)
        cv2.circle(mask, (radius, h-radius), radius, 255, -1)
        cv2.circle(mask, (w-radius, h-radius), radius, 255, -1)

        mask_3 = cv2.merge([mask, mask, mask])

        frame[y:y+h, x:x+w] = np.where(mask_3 == 255, glass, frame[y:y+h, x:x+w])

    def draw_profile(self, frame, face, name, relation, summary):
        fx1, fy1, fx2, fy2 = face.bbox.astype(int)
        face_w = fx2 - fx1

        # Use a different font
        font = cv2.FONT_HERSHEY_TRIPLEX

        if not name:
            text = "Unknown"
            tx = fx1 + face_w // 2 - 40
            ty = max(20, fy1 - 10)

            # Red color for unknown
            cv2.putText(frame, text, (tx, ty), font, 0.7, (0, 0, 255), 1)
            return

        fx1, fy1, fx2, fy2 = face.bbox.astype(int)
        face_w = fx2 - fx1
        face_h = fy2 - fy1

        # HUD sizing
        card_w = max(240, face_w + 40)
        card_h = 96

        cx = fx1 + face_w // 2 - card_w // 2
        cy = max(10, fy1 - card_h - 14)

        cx = max(10, min(cx, frame.shape[1] - card_w - 10))

        self.draw_glass_hud(frame, cx, cy, card_w, card_h)

        pad = 18

        # Name (bold)
        cv2.putText(frame, name, (cx + pad, cy + 32),
                    font, 0.75, (0, 0, 0), 3)
        cv2.putText(frame, name, (cx + pad, cy + 32),
                    font, 0.75, (245, 245, 245), 2)

        # Relation
        cv2.putText(frame, relation, (cx + pad, cy + 58),
                    font, 0.58, (0, 0, 0), 2)
        cv2.putText(frame, relation, (cx + pad, cy + 58),
                    font, 0.58, (190, 220, 255), 1)

        # Summary
        cv2.putText(frame, summary, (cx + pad, cy + 82),
                    font, 0.55, (0, 0, 0), 2)
        cv2.putText(frame, summary, (cx + pad, cy + 82),
                    font, 0.55, (215, 235, 225), 1)

    def run(self, cam=0):
        cap = cv2.VideoCapture(cam)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        frame_idx = 0
        skip = 2
        cached_faces = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % skip == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                cached_faces = self.app.get(rgb)

            frame_idx += 1

            for face in cached_faces:
                emb = face.embedding.astype(np.float32)
                emb /= np.linalg.norm(emb)

                name, relation, summary = self.recognize(emb)
                self.draw_profile(frame, face, name, relation, summary)

            cv2.imshow("Live Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                self.load_embeddings()

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    print("Live Face Recognition — Floating Glass HUD")

    # List all users
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("DATABASE_NAME")]
    people = db["people"]

    users = list(people.distinct("user_id"))
    user_map = {}

    print("Select user:")
    for i, uid in enumerate(users, 1):
        doc = people.find_one({"user_id": uid})
        name = doc.get("name", "Unknown") if doc else "Unknown"
        print(f"{i}. {uid}")
        user_map[i] = uid

    choice = int(input("Enter number: ").strip())
    selected_user_id = user_map.get(choice)

    recognizer = LiveFaceRecognitionMongo(
        user_id=selected_user_id,
        similarity_threshold=0.3
    )
    recognizer.load_embeddings()
    recognizer.run()
