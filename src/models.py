from werkzeug.security import generate_password_hash, check_password_hash
from src import mongo

class User:
    # User model to handle CRUD operations for the 'users' collection in MongoDB.
    
    def __init__(self, username, email, password, role):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)  # Hash password before storing
        self.role = role

    def save(self):
        # Save the user to the database.
        mongo.db.users.insert_one({
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "role": self.role
        })

    @staticmethod
    def find_by_username(username):
        # Find a user by their username.
        user = mongo.db.users.find_one({"username": username})
        if user:
            return User.from_dict(user)
        return None

    @staticmethod
    def from_dict(data):
        # Create a User instance from a dictionary.
        return User(
            username=data['username'],
            email=data['email'],
            password=data['password'],  # Password is already hashed
            role=data['role']
        )

    def verify_password(self, password):
        # Check if the provided password matches the stored password.
        return check_password_hash(self.password, password)

    @staticmethod
    def find_all():
        # Retrieve all users.
        users = mongo.db.users.find()
        return [User.from_dict(user) for user in users]

    @staticmethod
    def update_user(username, update_data):
        # Update a user's information.
        mongo.db.users.update_one(
            {"username": username},
            {"$set": update_data}
        )

    @staticmethod
    def delete_user(username):
        # Delete a user by their username.
        mongo.db.users.delete_one({"username": username})

    def to_dict(self):
        # Convert the User instance to a dictionary.
        return {
            "username": self.username,
            "email": self.email,
            "password": self.password,  # This remains hashed
            "role": self.role
        }