"""
Simple Database Interface for Gymnastics Analysis System
Provides high-level database operations with connection pooling.
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Any
import json
from datetime import datetime


class SimpleDatabase:
    """High-level database interface with connection pooling."""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimpleDatabase, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is not set")
            
            # Parse connection string
            try:
                self._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=database_url
                )
            except Exception as e:
                raise ConnectionError(f"Failed to create connection pool: {e}")
    
    def _get_connection(self):
        """Get a connection from the pool."""
        if self._pool is None:
            raise ConnectionError("Database pool not initialized")
        return self._pool.getconn()
    
    def _return_connection(self, conn):
        """Return a connection to the pool."""
        if self._pool:
            self._pool.putconn(conn)
    
    def _execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> List[Dict]:
        """Execute a query and return results."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                conn.commit()
                return [dict(row) for row in result]
            else:
                conn.commit()
                return []
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Database query failed: {e}")
        finally:
            if conn:
                cursor.close()
                self._return_connection(conn)
    
    # ============================================
    # USER OPERATIONS
    # ============================================
    
    def create_user(self, email: str, password_hash: str, name: Optional[str] = None) -> Dict:
        """Create a new user."""
        query = """
            INSERT INTO users (email, password_hash, name)
            VALUES (%s, %s, %s)
            RETURNING id, email, name, created_at, updated_at
        """
        result = self._execute_query(query, (email, password_hash, name))
        if result:
            return result[0]
        raise Exception("Failed to create user")
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = %s"
        result = self._execute_query(query, (email,))
        return result[0] if result else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = %s"
        result = self._execute_query(query, (user_id,))
        return result[0] if result else None
    
    def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        query = "UPDATE users SET last_login = %s WHERE id = %s"
        try:
            self._execute_query(query, (datetime.now(), user_id), fetch=False)
            return True
        except:
            return False
    
    # ============================================
    # ANALYSIS OPERATIONS
    # ============================================
    
    def create_analysis(
        self,
        analysis_id: str,
        user_id: Optional[str],
        file_name: str,
        exercise_type: str,
        input_video_data: Optional[bytes] = None,
        mime_type: str = "video/mp4"
    ) -> Dict:
        """Create a new analysis record."""
        query = """
            INSERT INTO analyses (id, user_id, file_name, exercise_type, input_video, input_video_size, input_video_mime_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, file_name, exercise_type, status, created_at
        """
        video_size = len(input_video_data) if input_video_data else None
        result = self._execute_query(
            query,
            (analysis_id, user_id, file_name, exercise_type, input_video_data, video_size, mime_type)
        )
        if result:
            return result[0]
        raise Exception("Failed to create analysis")
    
    def get_analysis(self, analysis_id: str, include_videos: bool = False) -> Optional[Dict]:
        """Get analysis by ID."""
        if include_videos:
            query = "SELECT * FROM analyses WHERE id = %s"
        else:
            query = """
                SELECT id, user_id, file_name, exercise_type, status, progress, error_message,
                       overall_score, max_score, percentage, results_json, json_report,
                       input_video_size, output_video_size, pdf_report_size,
                       input_video_mime_type, output_video_mime_type,
                       created_at, updated_at, completed_at
                FROM analyses WHERE id = %s
            """
        result = self._execute_query(query, (analysis_id,))
        return result[0] if result else None
    
    def update_analysis_status(
        self,
        analysis_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
        exercise_type: Optional[str] = None
    ) -> bool:
        """Update analysis processing status."""
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if progress is not None:
            updates.append("progress = %s")
            params.append(progress)
        if error_message is not None:
            updates.append("error_message = %s")
            params.append(error_message)
        if exercise_type is not None:
            updates.append("exercise_type = %s")
            params.append(exercise_type)
        
        if not updates:
            return False
        
        params.append(analysis_id)
        query = f"UPDATE analyses SET {', '.join(updates)} WHERE id = %s"
        
        try:
            self._execute_query(query, tuple(params), fetch=False)
            return True
        except:
            return False
    
    def save_analysis_results(
        self,
        analysis_id: str,
        overall_score: Optional[float] = None,
        max_score: Optional[float] = None,
        percentage: Optional[float] = None,
        results_json: Optional[Dict] = None
    ) -> bool:
        """Save analysis results."""
        updates = []
        params = []
        
        if overall_score is not None:
            updates.append("overall_score = %s")
            params.append(overall_score)
        if max_score is not None:
            updates.append("max_score = %s")
            params.append(max_score)
        if percentage is not None:
            updates.append("percentage = %s")
            params.append(percentage)
        if results_json is not None:
            updates.append("results_json = %s")
            params.append(json.dumps(results_json))
        
        updates.append("status = %s")
        params.append("completed")
        updates.append("completed_at = %s")
        params.append(datetime.now())
        
        params.append(analysis_id)
        query = f"UPDATE analyses SET {', '.join(updates)} WHERE id = %s"
        
        try:
            self._execute_query(query, tuple(params), fetch=False)
            return True
        except Exception as e:
            print(f"Error saving results: {e}")
            return False
    
    def store_input_video(self, analysis_id: str, video_data: bytes, mime_type: str = "video/mp4") -> bool:
        """Store input video blob."""
        query = """
            UPDATE analyses 
            SET input_video = %s, input_video_size = %s, input_video_mime_type = %s
            WHERE id = %s
        """
        try:
            self._execute_query(query, (video_data, len(video_data), mime_type, analysis_id), fetch=False)
            return True
        except:
            return False
    
    def store_output_video(self, analysis_id: str, video_data: bytes, mime_type: str = "video/mp4") -> bool:
        """Store output video blob."""
        query = """
            UPDATE analyses 
            SET output_video = %s, output_video_size = %s, output_video_mime_type = %s
            WHERE id = %s
        """
        try:
            self._execute_query(query, (video_data, len(video_data), mime_type, analysis_id), fetch=False)
            return True
        except:
            return False
    
    def store_pdf_report(self, analysis_id: str, pdf_data: bytes) -> bool:
        """Store PDF report."""
        query = """
            UPDATE analyses 
            SET pdf_report = %s, pdf_report_size = %s
            WHERE id = %s
        """
        try:
            self._execute_query(query, (pdf_data, len(pdf_data), analysis_id), fetch=False)
            return True
        except:
            return False
    
    def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        include_videos: bool = False
    ) -> List[Dict]:
        """Get all analyses for a user."""
        if include_videos:
            query = """
                SELECT * FROM analyses 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
        else:
            query = """
                SELECT id, user_id, file_name, exercise_type, status, progress, error_message,
                       overall_score, max_score, percentage, results_json, json_report,
                       input_video_size, output_video_size, pdf_report_size,
                       input_video_mime_type, output_video_mime_type,
                       created_at, updated_at, completed_at
                FROM analyses 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
        return self._execute_query(query, (user_id, limit, offset))
    
    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete an analysis."""
        query = "DELETE FROM analyses WHERE id = %s"
        try:
            self._execute_query(query, (analysis_id,), fetch=False)
            return True
        except:
            return False
    
    # ============================================
    # SESSION OPERATIONS
    # ============================================
    
    def create_session(self, user_id: str, session_token: str, expires_at: datetime) -> Dict:
        """Create a session."""
        query = """
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, session_token, expires_at, created_at
        """
        result = self._execute_query(query, (user_id, session_token, expires_at))
        if result:
            return result[0]
        raise Exception("Failed to create session")
    
    def get_session(self, session_token: str) -> Optional[Dict]:
        """Get session by token."""
        query = """
            SELECT * FROM sessions 
            WHERE session_token = %s AND expires_at > %s
        """
        result = self._execute_query(query, (session_token, datetime.now()))
        return result[0] if result else None
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session."""
        query = "DELETE FROM sessions WHERE session_token = %s"
        try:
            self._execute_query(query, (session_token,), fetch=False)
            return True
        except:
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions."""
        query = "DELETE FROM sessions WHERE expires_at < %s"
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now(),))
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return deleted
        except:
            if conn:
                conn.rollback()
                self._return_connection(conn)
            return 0


# Singleton instance
_database_instance = None

def get_database() -> SimpleDatabase:
    """Get the database singleton instance."""
    global _database_instance
    if _database_instance is None:
        _database_instance = SimpleDatabase()
    return _database_instance
