import json
import os
import sys
from sqlalchemy.orm import Session

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from app.models.exercise import Exercise
from app.models.analytical_model import AnalyticalModel
from app.models.training_data import TrainingData

def migrate_exercises(db: Session):
    print("Migrating exercises...")
    with open('../app/config.json', 'r') as f:
        config_data = json.load(f)
    
    exercises = config_data.get("exercises", [])
    for ex_data in exercises:
        exercise = db.query(Exercise).filter_by(name=ex_data['name']).first()
        if not exercise:
            exercise = Exercise(name=ex_data['name'], description=ex_data.get('description'))
            db.add(exercise)
            print(f"  Added exercise: {exercise.name}")
    
    db.commit()
    print("Exercises migration complete.")

def migrate_analytical_models(db: Session):
    print("\nMigrating analytical models...")
    with open('../app/analytical_models/analytical0.json', 'r') as f:
        model_data = json.load(f)
    
    # Assuming the model is for the first exercise found
    exercise = db.query(Exercise).first()
    if not exercise:
        print("  No exercises found in the database. Cannot migrate analytical model.")
        return

    model_name = "Default Analytical Model"
    analytical_model = db.query(AnalyticalModel).filter_by(name=model_name).first()
    if not analytical_model:
        analytical_model = AnalyticalModel(
            name=model_name,
            exercise_id=exercise.id,
            model_data=model_data
        )
        db.add(analytical_model)
        print(f"  Added analytical model '{model_name}' for exercise '{exercise.name}'.")

    db.commit()
    print("Analytical models migration complete.")

def migrate_training_data(db: Session):
    print("\nMigrating training data...")
    # --- Training Data Migration Placeholder ---
    # The original training data CSV files (e.g., beoordeling.csv) were not found.
    # When you locate them, place them in a known directory and update this function.
    #
    # Example for reading a CSV:
    # import pandas as pd
    # training_file_path = 'path/to/your/beoordeling.csv'
    # if os.path.exists(training_file_path):
    #     df = pd.read_csv(training_file_path)
    #     exercise = db.query(Exercise).filter_by(name="Your Exercise Name").first()
    #     if exercise:
    #         for _, row in df.iterrows():
    #             scores = row.to_dict() # Or process as needed
    #             training_record = TrainingData(
    #                 exercise_id=exercise.id,
    #                 source_description=f"From {os.path.basename(training_file_path)}",
    #                 scores=scores
    #             )
    #             db.add(training_record)
    #     db.commit()
    #     print(f"  Migrated data from {training_file_path}")
    # else:
    #     print("  Training data file not found. Skipping.")
    print("  Training data migration skipped (placeholder).")


def main():
    db = SessionLocal()
    try:
        migrate_exercises(db)
        migrate_analytical_models(db)
        migrate_training_data(db)
        print("\nData migration finished successfully.")
    except Exception as e:
        print(f"\nAn error occurred during data migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
