# Samplyze

**Version: 1.0.0**

**Samplyze** is a comprehensive, self-contained, and **offline-first** Laboratory Information & Management System (LIMS) built with **Python** and **Flask**. This system handles the complete workflow of a laboratory, from applicant registration and sample tracking to multi-step diagnosis, reporting, and internal collaboration tools.

---

## 🚀 Key Features

### 🔧 Core & Usability

* **Offline First**: All essential assets are served locally, allowing the application to function without an internet connection.
* **Role-Based Access Control**: A flexible permission system allows administrators to create custom roles and assign specific permissions for each module.
* **Print-Friendly Reports & Cards**: Generate clean, print-ready reports and ID cards for applicants, samples, and visitors using the browser's native print functionality.
* **Production-Ready Deployment**: Uses the **Waitress WSGI server** for stable and reliable performance.

---

### 🛠️ Administrator Portal

* **Admin Dashboard**: An at-a-glance overview of the total number of staff, applicants, and samples.
* **Staff & Role Management**: Add new staff members, create custom roles (e.g., "Lab Technician," "Front Office"), and assign granular permissions for each feature.
* **System Configuration**: Customize the lab's name, logo, and contact details, which appear on all reports.
* **Data Management**:

  * Create full-system backups
  * Restore from a backup file
  * Migrate data from older versions of the database
* **Audit Trail**: A comprehensive, searchable log of all key actions performed by users, with an option to export the log as a CSV file.

---

### 👨‍💪 Staff & Consultant Portal

* **Applicant & Sample Management**: A complete lifecycle management system for tracking applicants and their associated samples, with unique IDs, status updates, and detailed records.
* **Dual Consultancy Tracks**:

  * **Sampled Consultancies (SC)** with multi-step diagnoses
  * **Non-Sampled Consultancies (NSC)** for simpler evaluations
* **Rich Text Diagnosis**: A rich text editor (with table support) is integrated into the diagnosis module, allowing for formatted results and observations.
* **Internal Mail System**: A secure messaging system for staff to communicate and share file attachments, with notifications for unread mail.
* **Folder-Based File Sharing**: Create shared folders, manage user-specific permissions, and upload/download files via a drag-and-drop interface.
* **Equipment Logging**: Track the usage and history of lab equipment with a live check-in/check-out system and CSV import/export.
* **Knowledge Base**: A central repository for standardized diagnoses and remedies. Staff can quickly populate forms with pre-defined data, ensuring consistency and efficiency.
* **Visitor Management**: A complete system to register visitors, capture their photos via webcam, log entry/exit times, and print visitor passes with barcodes.

---

## 🧪 Tech Stack

* **Backend**: Python 3, Flask
* **Database**: SQLite (with SQLAlchemy ORM)
* **Forms & Validation**: Flask-WTF, WTForms
* **Server**: Waitress WSGI Server
* **Frontend**: Bootstrap 5, JavaScript, Quill.js
* **Authentication**: Flask-Login

---

## ⚙️ Getting Started

### 📋 Prerequisites

* Python 3.10 or newer
* pip (Python package installer)

---

### 📦 Installation

```bash
# Clone the repository
git clone <your-repository-url>
cd samplyze-project

# Create and activate a virtual environment

# On Windows:
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

---

### ▶️ How to Run the Application

Make sure your virtual environment is activated, then:

```bash
python run.py
```

* This will start the **Waitress** server and automatically open the application in your default web browser at:
  [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔐 Password Management

### Default Login

When the application is first run, a default administrator account is created:

```text
Username: admin
Password: password
```

---

### Changing Your Password (as Admin)

1. Log in as the admin user.
2. Click on your name in the top-right corner of the navigation bar.
3. Select **"Change Password"** from the dropdown menu.

---

### Resetting a Forgotten Admin Password

If you forget the admin password, you can reset it back to the default using the provided command-line script:

1. Stop the running server (press `Ctrl+C` in the terminal).
2. Activate your virtual environment.
3. Run the following command from the project root:

```bash
python reset_admin_password.py
```

4. Follow the prompts to confirm the reset.
5. Restart the application with:

```bash
python run.py
```


## 📫 Contact

For feedback, bug reports, or feature requests, please open an issue or submit a pull request.

---

> © 2025 Samplyze | Built with ❤️ from Enscygen
