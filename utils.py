import random
import string
import os
from models import Applicant, SampleSC

def generate_uid():
    """Generates a unique 10-digit alphanumeric UID for an applicant."""
    while True:
        uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if not Applicant.query.filter_by(uid=uid).first():
            return uid

def generate_sample_uid():
    """Generates a unique 12-digit alphanumeric UID for a sample."""
    while True:
        sample_uid = 'SMP' + ''.join(random.choices(string.digits, k=9))
        if not SampleSC.query.filter_by(sample_uid=sample_uid).first():
            return sample_uid
