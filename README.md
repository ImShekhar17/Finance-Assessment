# Finance Backend API Assessment

## Overview
A comprehensive Django-based backend for financial record management, featuring multi-role access control (RBAC), secure JWT authentication, and real-time dashboard analytics.

## 🚀 Quick Access
- **Welcome API (Root)**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **OpenAPI Specification**: `schema.yml` (located in root folder)

> [!TIP]
> **Standalone Documentation**: I have included a standalone `schema.yml` (OpenAPI Spec) in the repository root. This file can be imported into tools like [Swagger Editor](https://editor.swagger.io/) or Postman to view the full API documentation offline.
>
> **Spec Glimpse:**
> ```yaml
> openapi: 3.0.3
> info:
>   title: Finance Backend API
>   version: 1.0.0
>   description: A comprehensive Django-based backend for financial record management.
> paths:
>   /api/auth/login/:
>     post:
>       summary: Unified login (Email, Mobile, App ID, Membership ID)
> ```
- **Admin Panel**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Core Flow & Logic
1. **Signup Workflow**:
   - Register via `/api/auth/signup/`. An OTP is sent to your email.
   - Verify OTP via `/api/auth/verify-otp/`. Upon success, your account is activated and a unique **Application ID** is sent to your email.
   - Resend OTP via `/api/auth/resend-otp/` if needed (max 3 requests per 10 mins).
2. **Authentication**:
   - Log in via `/api/auth/login/` using **Email**, **Mobile**, **App ID**, or **Membership ID**.
   - Password and OTP login methods are both supported.
3. **Role Enforcement**:
    - **ADMIN**: Has unrestricted access to all users and financial records.
    - **ANALYST**: Can manage (create/read/update/delete) records they own and access dashboard summaries.
    - **VIEWER**: Read-only access to dashboard data and personal records.
3. **Data Integrity**: Financial amounts are strictly validated to be positive. Each record is linked to a user for ownership tracking.
4. **Soft Delete**: Records are never truly deleted; they are marked with a `deleted_at` timestamp and excluded from queries automatically.
5. **Rate Limiting**: APIs are protected against brute-force and scraping with a default limit of 1000 requests/day for users.
6. **Pagination**: Large datasets are paginated by default (10 records per page) to ensure optimal performance.

- **Authentication**: Secure JWT-based authentication (Access & Refresh tokens).

---

## Tech Stack
- **Framework**: Django & Django Rest Framework (DRF)
- **Database**: MySQL
- **Auth**: Simple JWT
- **Validation**: DRF Serializers with custom validation logic.

---

## Detailed API Documentation

### 1. Unified Authentication & Signup

- **Signup (Step 1)**
  - `POST /api/auth/signup/`
  - **Request Body (JSON):**
    ```json
    {
      "username": "shekhar_dev",
      "email": "shekhar@example.com",
      "password": "secure_password123",
      "mobile_number": "9876543210",
      "name": "Shekhar Sharma",
      "role": "ANALYST"
    }
    ```
  - **Response:** `201 Created` with "Signup successful. OTP sent to your email."

- **Verify OTP (Step 2)**
  - `POST /api/auth/verify-otp/`
  - **Request Body (JSON):**
    ```json
    {
      "email": "shekhar@example.com",
      "otp": "123456"
    }
    ```
  - **Response:** `200 OK` with "OTP verified. Signup complete. Application ID has been sent to your email."

- **Resend OTP**
  - `POST /api/auth/resend-otp/`
  - **Request Body (JSON):**
    ```json
    {
      "email": "shekhar@example.com"
    }
    ```

- **Advanced Login**
  - `POST /api/auth/login/`
  - **Login Methods Support (JSON):**
    
    *Case 1: Email & Password*
    ```json
    {"email": "admin@gmail.com", "password": "admin"}
    ```
    
    *Case 2: Mobile Number & Password*
    ```json
    {"mobile_number": "1234567890", "password": "password123"}
    ```
    
    *Case 3: Application ID & Password*
    ```json
    {"application_id": "APP-001", "password": "password123"}
    ```
    
    *Case 4: Membership ID & Password*
    ```json
    {"membership_id": "MEM-001", "password": "password123"}
    ```
    
    *Case 5/6: OTP-based Login (Email or App ID)*
    ```json
    {"email": "user@example.com", "otp": "123456"}
    ```
  
  - **Success Response (200 OK):**
    ```json
    {
      "message": "Login successful.",
      "user": {
        "id": 1,
        "email": "admin@gmail.com",
        "mobile_number": "1234567890",
        "application_id": "APP-001",
        "membership_id": "MEM-001",
        "name": "Admin User"
      },
      "access": "<access_token>",
      "refresh": "<refresh_token>"
    }
    ```

- **Request Password Reset**
  - `POST /api/auth/password-reset/`
  - **Request Body (JSON):**
    ```json
    {
      "email": "admin@gmail.com"
    }
    ```
  - **Success Response (200 OK):**
    ```json
    {
      "message": "Password reset link sent to your email."
    }
    ```

- **Confirm Password Reset**
  - `POST /api/auth/password-reset-confirm/?uid=<uid>&token=<token>`
  - **Request Body (JSON):**
    ```json
    {
      "new_password": "new_secure_password123"
    }
    ```
  - **Success Response (200 OK):**
    ```json
    {
      "message": "Password has been reset successfully."
    }
    ```

---

### 2. User & Role Management (Admin Only)
- **Register New User**
  - `POST /api/users/`
  - **Request Body (JSON):**
    ```json
    {
      "username": "shekhar_analyst",
      "email": "shekhar@example.com",
      "password": "secure_password",
      "role": "ANALYST"
    }
    ```
  - **Success Response (201 Created):**
    ```json
    {
      "id": 2,
      "username": "shekhar_analyst",
      "email": "shekhar@example.com",
      "role": "ANALYST",
      "is_active": true
    }
    ```

---

### 3. Financial Records Management
- **List Records (Filtered by Ownership & Paginated)**
  - `GET /api/records/`
  - **Success Response (200 OK):**
    ```json
    {
      "count": 1,
      "next": null,
      "previous": null,
      "results": [
        {
          "id": 1,
          "user": 2,
          "user_name": "admin",
          "amount": "500.00",
          "type": "INCOME",
          "category": "Consulting",
          "date": "2024-04-05",
          "description": "Monthly consulting fee",
          "created_at": "2026-04-05T17:04:55Z"
        }
      ]
    }
    ```

- **Search & Filter Records**
  - `GET /api/records/?search=Consulting&type=INCOME`
  - Supports searching in `description` and `category`.
  - Supports filtering by `type`, `category`, and `date`.

- **Create Record**
  - `POST /api/records/`
  - **Request Body (JSON):**
    ```json
    {
      "amount": 250.00,
      "type": "EXPENSE",
      "category": "Office Supplies",
      "date": "2024-04-05",
      "description": "Stationery and printer ink"
    }
    ```

---

### 4. Dashboard Insights
- **Get Financial Summary Stats**
  - `GET /api/dashboard/summary/`
  - **Success Response (200 OK):**
    ```json
    {
      "total_income": 500.0,
      "total_expense": 0.0,
      "net_balance": 500.0,
      "category_totals": [
        {
          "category": "Consulting",
          "type": "INCOME",
          "total": 500.0
        }
      ],
      "recent_activity": [
        {
          "id": 1,
          "user": 2,
          "amount": "500.00",
          "type": "INCOME",
          "category": "Consulting",
          "date": "2024-04-05",
          "description": "Monthly consulting fee"
        }
      ],
      "role": "ADMIN"
    }
    ```

---

## Technical Setup & Deployment

### 1. Environment Configuration
The project uses a `.env` file for secure credential management.
1. Create a `.env` file in the `assessment/` root.
2. Add your MySQL credentials:
   ```env
   DB_NAME=finance_db
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_HOST=localhost
   DB_PORT=3306

   # Admin Account
   ADMIN_USERNAME=admin
   ADMIN_EMAIL=admin@gmail.com
   ADMIN_PASSWORD=admin
   ```

### 2. Installation
```bash
# Activate Virtual Environment
.\venv\Scripts\activate

# Install Core Dependencies
pip install -r requirements.txt

# Execute Migrations
python manage.py migrate
```

### 3. Pre-configured Admin Account
Credentials are managed via the `.env` file. By default:
- **Email:** `admin@gmail.com`
- **Username:** `admin`
- **Password:** `admin`

---

3. **Data Integrity**: Invalid categories or negative amounts are rejected with `400 Bad Request`.

---

## Testing & Quality Assurance
The project includes a comprehensive suite of automated tests in `core/tests.py` covering:
- **Signup & OTP Flow**: Brand new registration, verification, and Application ID generation.
- **RBAC Enforcement**: Verifying that Viewers cannot create records and Analysts cannot access other users' data.
- **Soft Delete Logic**: Ensuring deleted records are excluded from API results.
- **Dashboard Summary**: Validating mathematical aggregations of income and expenses.
- **Password Reset**: Testing the secure token-based reset flow.

To run tests:
```bash
python manage.py test core
```
