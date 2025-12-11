# create_db.py
from db import engine, Base
import models  # pour que les classes soient importées

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Base de données initialisée.")