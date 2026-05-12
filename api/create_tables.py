import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import engine
from api.models import Base

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done! All tables created.")