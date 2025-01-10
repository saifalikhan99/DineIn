# DineIn

DineIn is a food ordering and delivery platform built using Django 3.1. It is designed to streamline food delivery within a university campus by providing distinct functionalities for admins, vendors, and users. The system is modular, comprising three key components: Admin Module, Vendor Module, and User Module.

---
<img src = "https://raw.githubusercontent.com/ariz565/Learning---AI-ML/refs/heads/main/WhatsApp%20Image%202025-01-10%20at%2017.16.27_779cdc1d.jpg?token=GHSAT0AAAAAACPVIOCFBVZA2Q2DRVNVRJCIZ4BC4GQ">

## Functional Requirements

### 1. Admin Module
The Admin Module provides comprehensive tools for managing the platform, vendors, users, and orders.

#### Dashboard
- **Overview**: Summarizes key metrics, offering a high-level view of platform performance.
- **Status Cards**: Displays metrics such as total users, total vendors, total orders, and active orders.
- **Notifications**: Alerts about newly joined vendors, recent user activities, and current order statuses.
- **Sign Out**: Allows secure logout for administrators.

#### Vendor Management
- **Vendor Registration**: Add new vendors with details like business name, location, menu, and contact info.
- **Vendor Listing**: View a list of all registered vendors, categorized as active, pending, or suspended.
- **Vendor Suspension/Activation**: Manage vendor access by activating or suspending accounts.

#### Order Management
- **Order Overview**: Month-on-month sales data and total orders categorized.
- **Order Details**: Information such as order ID, customer name, vendor, order status, delivery time, and amount.
- **Order Tracking**: Real-time tracking and status updates.

#### User Management
- **User Listing**: View all registered users with details like name, email, and role.
- **User Deletion**: Delete inactive or problematic users.

---

### 2. Vendor Module
The Vendor Module empowers vendors to manage their business effectively on the platform.

#### Vendor Dashboard
- **Overview**: Key metrics such as total orders, pending orders, and total revenue.
- **Order Notifications**: Real-time alerts for new incoming orders.

#### Menu Management
- **Menu Creation**: Add new items, including product name, description, image, and price.
- **Item Availability**: Mark items as in-stock or out-of-stock based on inventory.
- **Menu Updates**: Modify item details, including prices and availability.

#### Order Management
- **Order Listing**: View incoming orders with details like order time, items ordered, delivery address, and total price.
- **Order Status Update**: Update the order status to "Preparing," "Out for Delivery," or "Delivered."

---

### 3. User Module
The User Module focuses on providing a seamless experience for end-users.

#### User Authentication
- **User Registration**: Register with email verification.
- **Login**: Authenticate using registered credentials.
- **Password Reset**: Reset forgotten passwords.
- **Session Management**: Ensure secure user sessions.

#### Profile Management
- **Profile Information**: Update profile details like name, phone number, and profile picture.
- **Order History**: View a history of past orders, including dates, items, and statuses.
- **Address Management**: Add, edit, or delete delivery addresses.

#### Order Placement and Tracking
- **Browse Menu**: Browse menus of nearby vendors within a 5 km radius.
- **Order Placement**: Add items to the cart, apply discounts, and confirm orders.
- **Real-Time Order Tracking**: Track orders from preparation to delivery.
- **Order Cancellation**: Cancel orders within a specified timeframe.

---

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd dinein
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

4. Start the development server:
   ```bash
   python manage.py runserver
   ```

5. Access the application at `http://127.0.0.1:8000`.

---

## Technologies Used
- **Backend**: Django 
- **Database**: PostgreSQL (default, configurable for production)
- **Frontend**: HTML, CSS, JavaScript (extendable)

---

## Features
- Role-based functionality for admins, vendors, and users.
- Real-time notifications and order tracking.
- Comprehensive vendor and menu management.
- Secure user authentication and session management.

---

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b main/DineIn
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your message here"
   ```
4. Push the branch:
   ```bash
   git push origin main/DineIn
   ```
5. Open a pull request.

---

## License
This project is licensed under the [MIT License](LICENSE).

---
