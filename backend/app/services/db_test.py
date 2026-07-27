import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import SessionLocal
from app.models import MTRItem
db = SessionLocal()
item = db.query(MTRItem).filter(MTRItem.mtr_code == 'MTR-0001').first()
print('mtr_code:', item.mtr_code)
print('properties:', item.properties)
print('item_type:', item.item_type)
print('dn:', item.properties.get('dn') if item.properties else None)
db.close()
