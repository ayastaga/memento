"""
Migration script to add face embeddings to existing people in MongoDB
This will process all people without embeddings and try to generate them from their photos
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import base64
import cv2
import numpy as np
from insightface.app import FaceAnalysis

load_dotenv()

# Initialize face recognition model
print("Initializing face recognition model...")
face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)
face_app.prepare(ctx_id=0, det_size=(640, 640))
print("Model ready!")

def generate_face_embedding(base64_image):
    """Generate face embedding from base64 encoded image"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Decode base64 to image
        img_data = base64.b64decode(base64_image)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None, "Failed to decode image"
        
        # Detect faces
        faces = face_app.get(img)
        
        if len(faces) == 0:
            return None, "No face detected"
        
        if len(faces) > 1:
            return None, "Multiple faces detected"
        
        # Extract and normalize embedding
        embedding = faces[0].embedding.astype(np.float32)
        embedding /= np.linalg.norm(embedding)
        
        return embedding.tolist(), None
        
    except Exception as e:
        return None, str(e)

def migrate_embeddings():
    """Add embeddings to all people without them"""
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('DATABASE_NAME')]
    people_collection = db['people']
    
    # Find all people without embeddings
    people_without_embeddings = list(people_collection.find({
        '$or': [
            {'embedding': {'$exists': False}},
            {'embedding': None}
        ]
    }))
    
    print(f"\nFound {len(people_without_embeddings)} people without embeddings")
    
    if len(people_without_embeddings) == 0:
        print("Nothing to migrate!")
        return
    
    print("\nStarting migration...\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for person in people_without_embeddings:
        person_name = person.get('name', 'Unknown')
        person_id = person['_id']
        
        # Check if person has a photo
        if not person.get('photo'):
            print(f"⊘ Skipping {person_name}: No photo available")
            skipped_count += 1
            continue
        
        print(f"Processing: {person_name}...", end=' ')
        
        # Generate embedding
        embedding, error = generate_face_embedding(person['photo'])
        
        if error:
            print(f"✗ Failed: {error}")
            failed_count += 1
        elif embedding:
            # Update person with embedding
            people_collection.update_one(
                {'_id': person_id},
                {
                    '$set': {
                        'embedding': embedding,
                        'embedding_dim': len(embedding)
                    }
                }
            )
            print(f"✓ Success (embedding size: {len(embedding)})")
            success_count += 1
        else:
            print("✗ Failed: Unknown error")
            failed_count += 1
    
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed:  {failed_count}")
    print(f"⊘ Skipped: {skipped_count}")
    print("="*60)
    
    if success_count > 0:
        print(f"\n{success_count} people now have face embeddings and can be recognized!")
    
    if failed_count > 0:
        print(f"\n{failed_count} people failed face detection. This could be because:")
        print("  - The photo doesn't contain a clear face")
        print("  - The face is at an angle or partially obscured")
        print("  - Multiple faces are in the photo")
        print("  - The image quality is too low")
        print("\nYou can try uploading better photos for these people.")

def verify_embeddings():
    """Verify how many people have embeddings"""
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('DATABASE_NAME')]
    people_collection = db['people']
    
    total = people_collection.count_documents({})
    with_embeddings = people_collection.count_documents({
        'embedding': {'$exists': True, '$ne': None}
    })
    without_embeddings = total - with_embeddings
    
    print("\n" + "="*60)
    print("Current Status:")
    print("="*60)
    print(f"Total people: {total}")
    print(f"With embeddings: {with_embeddings} ({with_embeddings/total*100:.1f}%)" if total > 0 else "With embeddings: 0")
    print(f"Without embeddings: {without_embeddings}")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("Face Embedding Migration Tool")
    print("="*60)
    
    # First, show current status
    verify_embeddings()
    
    # Ask for confirmation
    print("\nThis will attempt to generate face embeddings for all people")
    print("without them. This process is safe and won't modify existing data.")
    response = input("\nProceed with migration? (y/n): ").strip().lower()
    
    if response == 'y':
        migrate_embeddings()
        print("\n")
        verify_embeddings()
    else:
        print("Migration cancelled.")
