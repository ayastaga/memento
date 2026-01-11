import cv2
import numpy as np
import time
import os
from pathlib import Path
from insightface.app import FaceAnalysis
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LiveFaceRecognitionMongo:
    def __init__(self, user_id=None, similarity_threshold=0.3):
        """
        Initialize the live face recognition system with MongoDB
        
        Args:
            user_id: MongoDB user ID to load faces for (optional, can prompt later)
            similarity_threshold: Minimum cosine similarity for face match (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.known_faces = {}
        self.user_id = user_id
        
        # Initialize MongoDB connection
        print("Connecting to MongoDB...")
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('DATABASE_NAME')]
        self.people_collection = self.db['people']
        print("Connected to MongoDB!")
        
        # Initialize FaceAnalysis with optimizations
        print("Initializing face detection model...")
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=(320, 320))  # Reduced from 640 for speed
        
        # Performance tracking
        self.fps_history = []
        self.max_fps_samples = 30
        
    def set_user(self, user_id):
        """Set the user ID and load their face embeddings"""
        self.user_id = user_id
        self.load_embeddings()
        
    def load_embeddings(self):
        """Load all face embeddings from MongoDB for the current user"""
        if not self.user_id:
            print("Warning: No user ID set. Please set a user ID first.")
            return
            
        print(f"Loading embeddings from MongoDB for user {self.user_id}...")
        self.known_faces = {}
        
        try:
            # Query MongoDB for all people belonging to this user
            people = self.people_collection.find({
                'user_id': self.user_id,
                'embedding': {'$exists': True}
            })
            
            count = 0
            for person in people:
                person_id = str(person['_id'])
                self.known_faces[person_id] = {
                    "name": person['name'],
                    "relationship": person['relation'],
                    "embedding": np.array(person['embedding'], dtype=np.float32)
                }
                
                print(f"Loaded: {person['name']} ({person['relation']})")
                count += 1
            
            print(f"Total faces loaded: {count}")
            
        except Exception as e:
            print(f"Error loading embeddings from MongoDB: {e}")
    
    def cosine_similarity(self, emb1, emb2):
        """Calculate cosine similarity between two embeddings"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def recognize_face(self, face_embedding):
        """
        Find the best match for a face embedding
        
        Returns:
            tuple: (name, relationship, similarity_score) or (None, None, 0)
        """
        if len(self.known_faces) == 0:
            return None, None, 0
        
        best_match = None
        best_similarity = 0
        
        for person_id, person_data in self.known_faces.items():
            similarity = self.cosine_similarity(face_embedding, person_data["embedding"])
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = person_data
        
        if best_similarity >= self.similarity_threshold:
            return best_match["name"], best_match["relationship"], best_similarity
        else:
            return "Unknown", "Unknown", best_similarity
    
    def draw_face_box(self, frame, face, name, relationship, similarity):
        """Draw bounding box and information on the frame"""
        # Get face bounding box
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Choose color based on recognition
        if name == "Unknown":
            color = (0, 0, 255)  # Red for unknown
        else:
            color = (0, 255, 0)  # Green for known
        
        # Draw rectangle around face
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Prepare text
        text_name = f"{name}"
        text_relation = f"{relationship}"
        text_confidence = f"{similarity:.2%}"
        
        # Calculate text background size
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # Get text sizes
        (w1, h1), _ = cv2.getTextSize(text_name, font, font_scale, thickness)
        (w2, h2), _ = cv2.getTextSize(text_relation, font, font_scale, thickness)
        (w3, h3), _ = cv2.getTextSize(text_confidence, font, font_scale, thickness)
        
        max_width = max(w1, w2, w3)
        total_height = h1 + h2 + h3 + 30
        
        # Draw background rectangle for text
        bg_y1 = max(0, y1 - total_height - 10)
        bg_y2 = y1
        bg_x1 = x1
        bg_x2 = x1 + max_width + 20
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Draw text
        y_offset = bg_y1 + h1 + 5
        cv2.putText(frame, text_name, (x1 + 5, y_offset), 
                   font, font_scale, (255, 255, 255), thickness)
        
        y_offset += h2 + 10
        cv2.putText(frame, text_relation, (x1 + 5, y_offset), 
                   font, font_scale, (200, 200, 200), thickness)
        
        y_offset += h3 + 10
        cv2.putText(frame, text_confidence, (x1 + 5, y_offset), 
                   font, font_scale, (150, 150, 150), thickness)
    
    def calculate_fps(self, frame_time):
        """Calculate and return average FPS"""
        if frame_time > 0:
            fps = 1.0 / frame_time
            self.fps_history.append(fps)
            
            if len(self.fps_history) > self.max_fps_samples:
                self.fps_history.pop(0)
            
            return np.mean(self.fps_history)
        return 0
    
    def run(self, camera_index=0, display_fps=True):
        """
        Run the live face recognition system
        
        Args:
            camera_index: Camera device index (0 for default webcam)
            display_fps: Whether to display FPS counter
        """
        # Check if user is set
        if not self.user_id:
            print("Error: No user ID set. Please set a user ID first.")
            return
            
        if len(self.known_faces) == 0:
            print("Warning: No faces loaded. Please add people to the database first.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        # Open webcam
        cap = cv2.VideoCapture(camera_index)
        
        # Set camera properties for lower latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Try to set resolution (may not work on all cameras)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not cap.isOpened():
            print("Error: Could not open webcam")
            return
        
        print("\n" + "="*50)
        print("Live Face Recognition Started")
        print("="*50)
        print("Press 'q' to quit")
        print("Press 'r' to reload embeddings from database")
        print("="*50 + "\n")
        
        frame_count = 0
        skip_frames = 2  # Process every 3rd frame for speed
        last_faces = []  # Store last detection results
        
        while True:
            start_time = time.time()
            
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break
            
            # Only process every nth frame
            if frame_count % skip_frames == 0:
                # Convert BGR to RGB for face detection
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                faces = self.app.get(rgb_frame)
                last_faces = faces  # Store for skipped frames
            else:
                faces = last_faces  # Use previous detection
            
            frame_count += 1
            
            # Process each detected face
            for face in faces:
                # Get embedding
                embedding = face.embedding.astype(np.float32)
                embedding /= np.linalg.norm(embedding)
                
                # Recognize face
                name, relationship, similarity = self.recognize_face(embedding)
                
                # Draw bounding box and info
                self.draw_face_box(frame, face, name, relationship, similarity)
            
            # Calculate and display FPS
            if display_fps:
                frame_time = time.time() - start_time
                fps = self.calculate_fps(frame_time)
                
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.putText(frame, f"Faces: {len(faces)}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display the frame
            cv2.imshow('Live Face Recognition', frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('r'):
                print("\nReloading embeddings from database...")
                self.load_embeddings()
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Application closed")


if __name__ == "__main__":
    # Configuration
    SIMILARITY_THRESHOLD = 0.3  # Adjust for stricter/looser matching (0.3-0.5 recommended)
    CAMERA_INDEX = 0  # 0 for default webcam, change if you have multiple cameras
    
    # Get user ID
    print("="*50)
    print("Live Face Recognition - MongoDB Version")
    print("="*50)
    user_id = input("Enter your MongoDB user ID: ").strip()
    
    if not user_id:
        print("Error: User ID is required")
        exit(1)
    
    # Create and run the recognition system
    recognizer = LiveFaceRecognitionMongo(
        user_id=user_id,
        similarity_threshold=SIMILARITY_THRESHOLD
    )
    
    recognizer.load_embeddings()
    recognizer.run(camera_index=CAMERA_INDEX, display_fps=True)
