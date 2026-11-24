import os
import sys

# Tambahkan root directory ke sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app

# Vercel Serverless Function entry point
app = create_app('production' if os.environ.get('VERCEL') else 'development')
