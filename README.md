# LMS – University Management System

A **Django-based University Management System prototype** that provides core academic operations for administrators, faculty, and students.

---

## Overview

This project is a full-stack web application built with Django and uses SQLite as its db. It serves as a prototype for managing university workflows — including student records, course assignments, and learning resources

---

##  Features

- **Role-Based Access Control** – Separate views and permissions for Admins, Faculty, and Students
- **Student Management** – Register and manage student profiles and enrollment
- **Course Management** – Create courses, assign instructors, manage enrollments
- **Learning Management** – Deliver and organize course materials and resources
- **Templates-Based UI** – Django HTML templates for a consistent, server-rendered interface
- **Lightweight Database** – SQLite for quick setup and prototyping

---

## Tech Stack

| Layer      | Technology             |
|------------|------------------------|
| Backend    | Python 3, Django       |
| Frontend   | HTML, Django Templates, Bootstrap |
| Database   | SQLite3                |

---

## Project Structure

```
LMS-university-management/
├── LMS/                # Django project settings and configuration
├── apps/               # Django apps (core modules)
├── templates/          # HTML templates for the UI
├── docs/               # Project documentation
├── db.sqlite3          # SQLite database
├── manage.py           # Django management script
└── .gitattributes
```

---
### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Uday10001/LMS-university-management.git
cd LMS-university-management

# 2. Create and activate a virtual environment
python -m venv venv
source venv\Scripts\activate       # On Mac: venv\bins\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply database migrations
python manage.py migrate

# 5. Create a superuser (admin account)
python manage.py createsuperuser

#6. To create some dummy data
python manage.py populate_data
python manage.py generate_sessions

# 7. Run the development server
python manage.py runserver


```
* **The app will he hosted at** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **To access the django inbuilt admin panel** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
---

Log in with the superuser credentials you created above to manage all data directly.

