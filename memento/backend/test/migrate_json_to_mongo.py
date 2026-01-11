"""
Migration script to import existing JSON face embeddings into MongoDB
"""

import json
import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime

def migrate_json_to_mongo(user_id, json_directory="enrollment/output"):
    """
    Migrate JSON embedding files to MongoDB
    
    Args:
        user_id: MongoDB user ID to associate the people with
        json_directory: Directory containing JSON embedding files
    """
    load_dotenv()
    
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('DATABASE_NAME')]
    people_collection = db['people']
    
    # Check if directory exists
    json_dir = Path(json_directory)
    if not json_dir.exists():
        print(f"Error: Directory '{json_directory}' not found")
        return
    
    # Find all JSON files
    json_files = list(json_dir.glob("*.json"))
    
    if len(json_files) == 0:
        print(f"No JSON files found in '{json_directory}'")
        return
    
    print(f"Found {len(json_files)} JSON file(s)")
    print()
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['id', 'name', 'relationship', 'embedding']
            if not all(field in data for field in required_fields):
                print(f"✗ Skipping {json_file.name}: Missing required fields")
                skipped += 1
                continue
            
            # Check if already migrated (by name and user_id)
            existing = people_collection.find_one({
                'user_id': user_id,
                'name': data['name']
            })
            
            if existing:
                print(f"⊘ Skipping {data['name']}: Already exists in database")
                skipped += 1
                continue
            
            # Create person document
            person = {
                'user_id': user_id,
                'name': data['name'],
                'relation': data['relationship'],
                'summary': f"Migrated from {json_file.name}",
                'photo': '',  # No photo in old JSON format
                'embedding': data['embedding'],
                'embedding_dim': data.get('embedding_dim', 512),
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'migrated_from': json_file.name
            }
            
            # Insert into MongoDB
            result = people_collection.insert_one(person)
            print(f"✓ Migrated: {data['name']} ({data['relationship']}) -> ID: {result.inserted_id}")
            migrated += 1
            
        except Exception as e:
            print(f"✗ Error processing {json_file.name}: {str(e)}")
            errors += 1
    
    print()
    print("="*70)
    print(f"Migration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print("="*70)
    
    if migrated > 0:
        print()
        print("⚠ Note: Migrated entries don't have photos.")
        print("You should:")
        print("  1. Add photos through the frontend/API")
        print("  2. This will automatically regenerate embeddings with the new photos")
        print("  3. Or keep using the old embeddings without photos")

def main():
    print("="*70)
    print("JSON to MongoDB Migration Tool")
    print("="*70)
    print()
    
    # Get user ID
    user_id = input("Enter MongoDB user ID to associate people with: ").strip()
    
    if not user_id:
        print("Error: User ID is required")
        return
    
    # Get JSON directory (optional)
    json_dir = input("Enter JSON directory [enrollment/output]: ").strip()
    if not json_dir:
        json_dir = "enrollment/output"
    
    print()
    print(f"User ID: {user_id}")
    print(f"JSON Directory: {json_dir}")
    print()
    
    confirm = input("Proceed with migration? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Migration cancelled")
        return
    
    print()
    migrate_json_to_mongo(user_id, json_dir)

if __name__ == "__main__":
    main()
