Samplyze
A comprehensive, self-contained web application built with Python and Flask for managing the complete workflow of a laboratory. This system handles everything from applicant registration and sample tracking to multi-step diagnosis, reporting, and internal file sharing.

Key Features
Role-Based Access Control: Separate portals for Administrators and Staff/Consultants with distinct permissions.

Complete Applicant Lifecycle: Track applicants from their first visit, manage personal and contact information, and view their entire consultancy history.

Dual Consultancy Tracks:

Sampled Consultancy (SC): Full-fledged sample management with unique IDs, detailed data entry, image attachments, and a multi-step diagnosis process.

Non-Sampled Consultancy (NSC): A streamlined process for consultations that do not involve a physical sample.

Dynamic File Management: Users can dynamically add multiple images or files with captions and previews when creating or editing records.

Folder-Based File Sharing: A dedicated module for staff to create shared folders, manage permissions, and upload/download files via a drag-and-drop interface.

Robust Data Integrity: Deleting primary records (like staff or departments) safely handles dependencies by un-assigning related records, preventing data corruption.

Offline Capability: All essential assets (Bootstrap CSS/JS, Icons) are served locally, allowing the application to function without an internet connection.

Print-Friendly Reporting: Generate clean, print-ready reports for applicants and samples using the browser's native print functionality.

Production-Ready Deployment: Uses the Waitress WSGI server for stable and reliable performance.

Tech Stack
Backend: Python 3, Flask

Database: SQLite (with SQLAlchemy ORM)

Forms & Validation: Flask-WTF, WTForms

Server: Waitress WSGI Server

Frontend: Bootstrap 5, JavaScript

Authentication: Flask-Login

Getting Started
Follow these instructions to get a copy of the project up and running on your local machine.

Prerequisites
Python 3.10 or newer.

pip (Python package installer).

Installation
Clone the repository:

git clone <your-repository-url>
cd lab_management_system

Create and activate a virtual environment:

On Windows:

python -m venv venv
.\venv\Scripts\activate

On macOS/Linux:

python3 -m venv venv
source venv/bin/activate

Install the required packages:

pip install -r requirements.txt

How to Run the Application
Make sure your virtual environment is activated.

Run the run.py script from the root of the project directory:

python run.py

This will start the Waitress server and automatically open the application in your default web browser at http://127.0.0.1:8000.

Default Login
A default administrator account is created the first time you run the application.

Username: admin

Password: password

Log in as the admin to create departments and other staff accounts.

How to Use
Admin Setup: Log in as admin. Go to Manage Departments to create at least one department. Then, go to Manage Staff to create new user accounts.

Staff Login: Log out and log back in with a staff account.

Create Applicant: Navigate to Add OA to register a new applicant.

Manage Consultancies: From the applicant's profile page, you can start a new Sampled Consultancy (SC) or Non-Sampled Consultancy (NSC).

File Sharing: Access the File Sharing dashboard from the main navigation to create folders and share files with other users.

License
This project is licensed under the MIT License - see the LICENSE.md file for details.
