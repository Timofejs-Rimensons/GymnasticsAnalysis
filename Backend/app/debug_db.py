#!/usr/bin/env python3
"""
Database Testing Script
Tests all database operations to verify the setup is working correctly.
"""

import os
import sys
from database_simple import get_database
import bcrypt

def test_database():
    """Run comprehensive database tests."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    try:
        db = get_database()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("User Operations Test")
    print("=" * 60)
    
    try:
        # Test user creation
        test_email = "test@example.com"
        test_password = "test_password_123"
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Check if user exists, delete if so
        existing = db.get_user_by_email(test_email)
        if existing:
            print(f"⚠ Test user already exists, skipping creation")
            user_id = existing['id']
        else:
            user = db.create_user(
                email=test_email,
                password_hash=hashed_password,
                name="Test User"
            )
            user_id = user['id']
            print(f"✓ Created user: {user['email']} (ID: {user_id})")
        
        # Test user retrieval
        retrieved = db.get_user_by_id(user_id)
        if retrieved:
            print(f"✓ Retrieved user: {retrieved['email']}")
        else:
            print("✗ Failed to retrieve user")
            return False
        
        # Test last login update
        if db.update_user_last_login(user_id):
            print("✓ Updated last login timestamp")
        
    except Exception as e:
        print(f"✗ User operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("Analysis Operations Test")
    print("=" * 60)
    
    try:
        # Test analysis creation
        fake_video_data = b"fake_video_data_for_testing" * 100
        
        analysis = db.create_analysis(
            user_id=user_id,
            file_name="test_handstand.mp4",
            exercise_type="handstand",
            input_video_data=fake_video_data,
            mime_type="video/mp4"
        )
        analysis_id = analysis['id']
        print(f"✓ Created analysis: {analysis_id}")
        print(f"  - File: {analysis['file_name']}")
        print(f"  - Type: {analysis['exercise_type']}")
        print(f"  - Status: {analysis['status']}")
        
        # Test status update
        if db.update_analysis_status(analysis_id, status="processing", progress=0.5):
            print("✓ Updated analysis status")
        
        # Test results saving
        test_results = {
            "overall_score": 85.5,
            "max_score": 100,
            "categories": [
                {
                    "name": "Form",
                    "score": 90,
                    "max_score": 100
                }
            ]
        }
        
        if db.save_analysis_results(
            analysis_id=analysis_id,
            overall_score=85.5,
            max_score=100,
            percentage=85.5,
            results_json=test_results
        ):
            print("✓ Saved analysis results")
        
        # Test analysis retrieval
        retrieved_analysis = db.get_analysis(analysis_id, include_videos=False)
        if retrieved_analysis:
            print(f"✓ Retrieved analysis: {retrieved_analysis['file_name']}")
            print(f"  - Score: {retrieved_analysis.get('overall_score')}")
            print(f"  - Status: {retrieved_analysis['status']}")
        else:
            print("✗ Failed to retrieve analysis")
            return False
        
        # Test user analyses list
        user_analyses = db.get_user_analyses(user_id, limit=10)
        print(f"✓ Retrieved {len(user_analyses)} analyses for user")
        
        # Test output video storage
        fake_output = b"fake_output_video" * 100
        if db.store_output_video(analysis_id, fake_output):
            print("✓ Stored output video")
        
        # Cleanup test analysis
        if db.delete_analysis(analysis_id):
            print("✓ Deleted test analysis")
        
    except Exception as e:
        print(f"✗ Analysis operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("Session Operations Test")
    print("=" * 60)
    
    try:
        from datetime import datetime, timedelta
        
        session_token = "test_session_token_12345"
        expires_at = datetime.now() + timedelta(days=1)
        
        session = db.create_session(user_id, session_token, expires_at)
        print(f"✓ Created session: {session['id']}")
        
        retrieved_session = db.get_session(session_token)
        if retrieved_session:
            print(f"✓ Retrieved session: {retrieved_session['session_token']}")
        else:
            print("✗ Failed to retrieve session")
            return False
        
        if db.delete_session(session_token):
            print("✓ Deleted session")
        
    except Exception as e:
        print(f"✗ Session operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("All Tests Passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    # Check for DATABASE_URL
    if not os.getenv('DATABASE_URL'):
        print("Error: DATABASE_URL environment variable is not set")
        print("Set it with: export DATABASE_URL='postgresql://user:pass@host:port/db'")
        sys.exit(1)
    
    success = test_database()
    sys.exit(0 if success else 1)
