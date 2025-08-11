from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Restaurant(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    cuisine_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class MenuItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255))
    customizations = db.Column(db.Text)  # JSON string
    allergens = db.Column(db.Text)  # JSON string
    is_available = db.Column(db.Boolean, default=True)
    preparation_time = db.Column(db.Integer, default=15)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Table(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = db.Column(db.String(36), nullable=False)
    table_number = db.Column(db.String(10), nullable=False)
    qr_code = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer)
    location = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = db.Column(db.String(36), nullable=False)
    table_id = db.Column(db.String(36), nullable=False)
    customer_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    items = db.Column(db.Text, nullable=False)  # JSON string
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    special_requests = db.Column(db.Text)
    estimated_ready_time = db.Column(db.DateTime)
    bill_requested = db.Column(db.Boolean, default=False)
    bill_requested_at = db.Column(db.DateTime)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/qr-scanner')
def qr_scanner():
    return render_template('qr_scanner.html')

@app.route('/menu')
def menu():
    table_id = request.args.get('table', 'demo_table')
    return render_template('menu.html', table_id=table_id)

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

@app.route('/order-confirmation')
def order_confirmation():
    order_id = request.args.get('orderId')
    return render_template('order_confirmation.html', order_id=order_id)

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# API Routes
@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'description': r.description,
        'cuisine_type': r.cuisine_type,
        'address': r.address,
        'phone': r.phone,
        'email': r.email
    } for r in restaurants])

@app.route('/api/menu-items', methods=['GET'])
def get_menu_items():
    items = MenuItem.query.filter_by(is_available=True).all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'category': item.category,
        'image_url': item.image_url,
        'customizations': json.loads(item.customizations) if item.customizations else [],
        'allergens': json.loads(item.allergens) if item.allergens else [],
        'preparation_time': item.preparation_time,
        'is_available': item.is_available
    } for item in items])

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.order_by(Order.created_date.desc()).all()
    return jsonify([{
        'id': order.id,
        'restaurant_id': order.restaurant_id,
        'table_id': order.table_id,
        'customer_name': order.customer_name,
        'status': order.status,
        'items': json.loads(order.items),
        'subtotal': order.subtotal,
        'tax_amount': order.tax_amount,
        'total_amount': order.total_amount,
        'special_requests': order.special_requests,
        'estimated_ready_time': order.estimated_ready_time.isoformat() if order.estimated_ready_time else None,
        'bill_requested': order.bill_requested,
        'bill_requested_at': order.bill_requested_at.isoformat() if order.bill_requested_at else None,
        'created_date': order.created_date.isoformat()
    } for order in orders])

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    
    # Calculate estimated ready time
    avg_prep_time = 15  # Default 15 minutes
    if 'items' in data:
        total_prep = sum(item.get('preparation_time', 15) for item in data['items'])
        avg_prep_time = max(15, int(total_prep / len(data['items']) * 1.2))
    
    estimated_ready = datetime.utcnow() + timedelta(minutes=avg_prep_time)
    
    order = Order(
        restaurant_id=data['restaurant_id'],
        table_id=data['table_id'],
        customer_name=data.get('customer_name', ''),
        items=json.dumps(data['items']),
        subtotal=data['subtotal'],
        tax_amount=data['tax_amount'],
        total_amount=data['total_amount'],
        special_requests=data.get('special_requests', ''),
        estimated_ready_time=estimated_ready
    )
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({
        'id': order.id,
        'status': 'success',
        'estimated_ready_time': estimated_ready.isoformat()
    })

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.json
    
    for key, value in data.items():
        if hasattr(order, key):
            if key == 'bill_requested_at' and value:
                setattr(order, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
            else:
                setattr(order, key, value)
    
    order.updated_date = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'status': 'success'})

def init_sample_data():
    """Initialize the database with sample data"""
    if Restaurant.query.count() == 0:
        # Add sample restaurant
        restaurant = Restaurant(
            id="demo_restaurant",
            name="Bella Vista Restaurant",
            description="Authentic Italian cuisine with a modern twist",
            cuisine_type="Italian",
            address="123 Main Street, Downtown",
            phone="(555) 123-4567",
            email="info@bellavista.com"
        )
        db.session.add(restaurant)
        
        # Add sample menu items
        menu_items = [
            {
                "name": "Margherita Pizza",
                "description": "Fresh tomato sauce, mozzarella, basil leaves",
                "price": 16.99,
                "category": "main_course",
                "image_url": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400",
                "customizations": json.dumps([
                    {
                        "name": "Size",
                        "options": [
                            {"name": "Small", "price_modifier": 0},
                            {"name": "Large", "price_modifier": 4.00}
                        ]
                    }
                ]),
                "preparation_time": 12
            },
            {
                "name": "Caesar Salad",
                "description": "Crisp romaine lettuce, parmesan, croutons, caesar dressing",
                "price": 12.99,
                "category": "appetizer",
                "image_url": "https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400",
                "customizations": json.dumps([
                    {
                        "name": "Add Protein",
                        "options": [
                            {"name": "None", "price_modifier": 0},
                            {"name": "Grilled Chicken", "price_modifier": 5.00},
                            {"name": "Grilled Shrimp", "price_modifier": 7.00}
                        ]
                    }
                ]),
                "preparation_time": 5
            },
            {
                "name": "Grilled Salmon",
                "description": "Fresh Atlantic salmon with lemon herb butter, seasonal vegetables",
                "price": 24.99,
                "category": "main_course",
                "image_url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400",
                "allergens": json.dumps(["fish"]),
                "preparation_time": 18
            },
            {
                "name": "Chocolate Lava Cake",
                "description": "Warm chocolate cake with molten center, vanilla ice cream",
                "price": 8.99,
                "category": "dessert",
                "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400",
                "allergens": json.dumps(["eggs", "dairy", "gluten"]),
                "preparation_time": 8
            },
            {
                "name": "Fresh Juice",
                "description": "Daily selection of fresh pressed juices",
                "price": 5.99,
                "category": "beverage",
                "customizations": json.dumps([
                    {
                        "name": "Flavor",
                        "options": [
                            {"name": "Orange", "price_modifier": 0},
                            {"name": "Apple", "price_modifier": 0},
                            {"name": "Mixed Berry", "price_modifier": 1.00}
                        ]
                    }
                ]),
                "preparation_time": 2
            }
        ]
        
        for item_data in menu_items:
            item = MenuItem(
                restaurant_id="demo_restaurant",
                **item_data
            )
            db.session.add(item)
        
        # Add sample tables
        tables = [
            {"table_number": "1", "qr_code": "demo_table_1", "capacity": 2, "location": "window"},
            {"table_number": "2", "qr_code": "demo_table_2", "capacity": 4, "location": "main dining"},
            {"table_number": "3", "qr_code": "demo_table_3", "capacity": 6, "location": "patio"}
        ]
        
        for table_data in tables:
            table = Table(
                restaurant_id="demo_restaurant",
                **table_data
            )
            db.session.add(table)
        
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_sample_data()
    app.run(debug=True)