# Samplyze

**Version: 1.0.0**

A comprehensive, self-contained, and **offline-first** Laboratory Information & Management System (LIMS) built with **Python** and **Flask**. This system handles the complete workflow of a laboratory — from applicant registration and sample tracking to multi-step diagnosis, reporting, and internal collaboration tools.

---

## 🚀 Key Features

### 🔧 Core & Usability

- **Offline First**: All essential assets are served locally, allowing the application to function without an internet connection.
- **Role-Based Access Control**: Create custom roles and assign fine-grained permissions for each module.
- **Print-Friendly Reports & Cards**: Generate clean, print-ready reports and ID cards using the browser's native print functionality.
- **Production-Ready Deployment**: Uses the **Waitress WSGI server** for stable and reliable performance.

---

### 🛠️ Administrator Portal

- **Admin Dashboard**: At-a-glance overview of total staff, applicants, and samples.
- **Staff & Role Management**: Create new roles (e.g., *Lab Technician*, *Front Office*), assign permissions.
- **System Configuration**: Customize lab name, logo, and contact details for reports.
- **Data Management**:
  - Create full-system backups
  - Restore from backup
  - Migrate data from older databases
- **Audit Trail**: Searchable user activity log with CSV export.

---

### 👩‍🔬 Staff & Consultant Portal

- **Applicant & Sample Management**: Track lifecycle with unique IDs, statuses, and details.
- **Dual Consultancy Tracks**:
  - *Sampled Consultancies (SC)* with multi-step diagnosis
  - *Non-Sampled Consultancies (NSC)*
- **Rich Text Diagnosis**: Integrated rich text editor with table support.
- **Internal Mail System**: Secure staff messaging with file attachments and notifications.
- **Folder-Based File Sharing**: Drag-and-drop uploads, permission-based access.
- **Equipment Logging**: Check-in/out tracking with CSV import/export.
- **Knowledge Base**: Repository of standard diagnoses/remedies for fast form filling.
- **Visitor Management**: Register visitors with webcam photos, log entry/exit, print passes with barcodes.

---

## 🧪 Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (via SQLAlchemy ORM)
- **Forms & Validation**: Flask-WTF, WTForms
- **Frontend**: Bootstrap 5, JavaScript, Quill.js
- **Server**: Waitress WSGI Server
- **Authentication**: Flask-Login

---

## ⚙️ Getting Started

### 📋 Prerequisites

- Python 3.10 or newer
- pip (Python package installer)

---

### 📦 Installation

```bash
# Clone the repository
git clone <your-repository-url>
cd samplyze-project

# Create and activate virtual environment
# On Windows:
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
