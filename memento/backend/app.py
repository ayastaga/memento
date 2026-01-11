from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import jwt
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('DATABASE_NAME')]
users_collection = db['users']
items_collection = db['items']
people_collection = db['people']

# Create indexes for efficient querying
users_collection.create_index('email', unique=True)
items_collection.create_index([('user_id', 1), ('created_at', -1)])
people_collection.create_index([('user_id', 1), ('created_at', -1)])

SECRET_KEY = os.getenv('SECRET_KEY')

# Helper function to create JWT token
def create_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Helper function to verify JWT token
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

# Auth middleware
def auth_required(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

# Helper function to format user response
def format_user_response(user):
    """Format user object for API response"""
    user_data = {
        'id': str(user['_id']),
        'email': user['email'],
        'name': user['name'],
        'timezone': user.get('timezone', 'UTC'),
        'primaryCaregiver': user.get('primaryCaregiver', {}),
        'profileImage': user.get('profileImage')  # Return image directly
    }
    
    return user_data

# Routes
@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        profile_image = data.get('profileImage', '')
        timezone = data.get('timezone', 'UTC')
        primary_caregiver = data.get('primaryCaregiver', {})
        
        if not email or not password or not name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate caregiver information
        if not primary_caregiver.get('name') or not primary_caregiver.get('relationship') or not primary_caregiver.get('contact'):
            return jsonify({'error': 'Primary caregiver information is required'}), 400
        
        # Check if user exists
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 400
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user document - store image directly as base64 string
        user = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'profileImage': profile_image if profile_image else None,
            'timezone': timezone,
            'primaryCaregiver': {
                'name': primary_caregiver.get('name'),
                'relationship': primary_caregiver.get('relationship'),
                'contact': primary_caregiver.get('contact')
            },
            'createdAt': datetime.datetime.utcnow(),
            'updatedAt': datetime.datetime.utcnow()
        }

        result = users_collection.insert_one(user)
        token = create_token(result.inserted_id)
        
        # Get the created user for response
        created_user = users_collection.find_one({'_id': result.inserted_id})
        
        return jsonify({
            'token': token,
            'user': format_user_response(created_user)
        }), 201
        
    except Exception as e:
        print(f"Signup error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400
        
        # Find user
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        token = create_token(user['_id'])
        
        return jsonify({
            'token': token,
            'user': format_user_response(user)
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/me', methods=['GET'])
@auth_required
def get_current_user():
    try:
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(format_user_response(user)), 200
        
    except Exception as e:
        print(f"Get user error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/user/update-profile-image', methods=['POST'])
@auth_required
def update_profile_image():
    """Update user's profile image"""
    try:
        data = request.json
        new_image = data.get('image')
        
        if not new_image:
            return jsonify({'error': 'No image provided'}), 400
        
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user document with new image
        users_collection.update_one(
            {'_id': ObjectId(request.user_id)},
            {
                '$set': {
                    'profileImage': new_image,
                    'updatedAt': datetime.datetime.utcnow()
                }
            }
        )
        
        updated_user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        return jsonify(format_user_response(updated_user)), 200
        
    except Exception as e:
        print(f"Update profile image error: {str(e)}")
        return jsonify({'error': 'Failed to update profile image'}), 500

# CRUD Routes for Items
@app.route('/api/items', methods=['GET'])
@auth_required
def get_items():
    items = list(items_collection.find({'user_id': request.user_id}).sort('created_at', -1))
    for item in items:
        item['_id'] = str(item['_id'])
        item['created_at'] = item['created_at'].isoformat()
    return jsonify(items), 200

@app.route('/api/items', methods=['POST'])
@auth_required
def create_item():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    item = {
        'user_id': request.user_id,
        'title': title,
        'description': description or '',
        'created_at': datetime.datetime.utcnow()
    }
    
    result = items_collection.insert_one(item)
    item['_id'] = str(result.inserted_id)
    item['created_at'] = item['created_at'].isoformat()
    
    return jsonify(item), 201

@app.route('/api/items/<item_id>', methods=['PUT'])
@auth_required
def update_item(item_id):
    data = request.json
    
    item = items_collection.find_one({
        '_id': ObjectId(item_id),
        'user_id': request.user_id
    })
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    update_data = {'updated_at': datetime.datetime.utcnow()}
    if 'title' in data:
        update_data['title'] = data['title']
    if 'description' in data:
        update_data['description'] = data['description']
    
    items_collection.update_one(
        {'_id': ObjectId(item_id)},
        {'$set': update_data}
    )
    
    updated_item = items_collection.find_one({'_id': ObjectId(item_id)})
    updated_item['_id'] = str(updated_item['_id'])
    updated_item['created_at'] = updated_item['created_at'].isoformat()
    
    return jsonify(updated_item), 200

@app.route('/api/items/<item_id>', methods=['DELETE'])
@auth_required
def delete_item(item_id):
    result = items_collection.delete_one({
        '_id': ObjectId(item_id),
        'user_id': request.user_id
    })
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Item not found'}), 404
    
    return jsonify({'message': 'Item deleted'}), 200

# CRUD Routes for People
@app.route('/api/people', methods=['GET'])
@auth_required
def get_people():
    """Get all people for the authenticated user"""
    try:
        people = list(people_collection.find({'user_id': request.user_id}).sort('created_at', -1))
        for person in people:
            person['_id'] = str(person['_id'])
            person['created_at'] = person['created_at'].isoformat()
        return jsonify(people), 200
    except Exception as e:
        print(f"Get people error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/people', methods=['POST'])
@auth_required
def create_person():
    """Add a new person to the people collection"""
    try:
        data = request.json
        name = data.get('name')
        relation = data.get('relation')
        summary = data.get('summary')
        photo = data.get('photo')
        
        # Validate required fields
        if not name or not relation or not summary or not photo:
            return jsonify({'error': 'All fields are required'}), 400
        
        person = {
            'user_id': request.user_id,
            'name': name,
            'relation': relation,
            'summary': summary,
            'photo': photo,
            'created_at': datetime.datetime.utcnow(),
            'updated_at': datetime.datetime.utcnow()
        }
        
        result = people_collection.insert_one(person)
        person['_id'] = str(result.inserted_id)
        person['created_at'] = person['created_at'].isoformat()
        person['updated_at'] = person['updated_at'].isoformat()
        
        return jsonify(person), 201
    except Exception as e:
        print(f"Create person error: {str(e)}")
        return jsonify({'error': 'Failed to add person'}), 500

@app.route('/api/people/<person_id>', methods=['GET'])
@auth_required
def get_person(person_id):
    """Get a specific person by ID"""
    try:
        person = people_collection.find_one({
            '_id': ObjectId(person_id),
            'user_id': request.user_id
        })
        
        if not person:
            return jsonify({'error': 'Person not found'}), 404
        
        person['_id'] = str(person['_id'])
        person['created_at'] = person['created_at'].isoformat()
        person['updated_at'] = person['updated_at'].isoformat()
        
        return jsonify(person), 200
    except Exception as e:
        print(f"Get person error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/people/<person_id>', methods=['PUT'])
@auth_required
def update_person(person_id):
    """Update a person's information"""
    try:
        data = request.json
        
        person = people_collection.find_one({
            '_id': ObjectId(person_id),
            'user_id': request.user_id
        })
        
        if not person:
            return jsonify({'error': 'Person not found'}), 404
        
        update_data = {'updated_at': datetime.datetime.utcnow()}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'relation' in data:
            update_data['relation'] = data['relation']
        if 'summary' in data:
            update_data['summary'] = data['summary']
        if 'photo' in data:
            update_data['photo'] = data['photo']
        
        people_collection.update_one(
            {'_id': ObjectId(person_id)},
            {'$set': update_data}
        )
        
        updated_person = people_collection.find_one({'_id': ObjectId(person_id)})
        updated_person['_id'] = str(updated_person['_id'])
        updated_person['created_at'] = updated_person['created_at'].isoformat()
        updated_person['updated_at'] = updated_person['updated_at'].isoformat()
        
        return jsonify(updated_person), 200
    except Exception as e:
        print(f"Update person error: {str(e)}")
        return jsonify({'error': 'Failed to update person'}), 500

@app.route('/api/people/<person_id>', methods=['DELETE'])
@auth_required
def delete_person(person_id):
    """Delete a person from the collection"""
    try:
        result = people_collection.delete_one({
            '_id': ObjectId(person_id),
            'user_id': request.user_id
        })
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Person not found'}), 404
        
        return jsonify({'message': 'Person deleted successfully'}), 200
    except Exception as e:
        print(f"Delete person error: {str(e)}")
        return jsonify({'error': 'Failed to delete person'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
