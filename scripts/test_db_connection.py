#!/usr/bin/env python3
"""
Database connection test script for IPFS Gateway.

Tests connectivity to both development and production databases.
Usage: python scripts/test_db_connection.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()


def test_connection(db_url: str, db_name: str) -> bool:
    """Test database connection and basic operations.
    
    Args:
        db_url: Database connection string
        db_name: Human-readable name for the database
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ {db_name} connection successful!")
            print(f"   PostgreSQL version: {version}")
            
            # Test table existence
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name IN "
                "('users', 'files', 'audit_logs', 'task_status');"
            ))
            table_count = result.fetchone()[0]
            print(f"   Tables found: {table_count}/4")
            
            if table_count == 4:
                print(f"   ✓ All required tables present")
            elif table_count > 0:
                print(f"   ⚠ Warning: Only {table_count}/4 tables found")
            else:
                print(f"   ⚠ Warning: No tables found (migrations may be needed)")
            
            return True
    except Exception as e:
        print(f"❌ {db_name} connection failed!")
        print(f"   Error: {str(e)}")
        return False


def main():
    """Main test execution."""
    print("=" * 70)
    print("IPFS Gateway - Database Connection Test")
    print("=" * 70)
    print()
    
    # Get database URLs
    dev_url = os.getenv("DATABASE_URL")
    prod_url = os.getenv("DATABASE_URL_PROD")
    
    if not dev_url:
        print("❌ DATABASE_URL not found in environment variables!")
        return 1
    
    if not prod_url:
        print("⚠ DATABASE_URL_PROD not found in environment variables")
        print("  Skipping production database test")
        print()
    
    # Test development database
    print("Testing Development Database")
    print("-" * 70)
    dev_ok = test_connection(dev_url, "Development DB")
    print()
    
    # Test production database if configured
    prod_ok = True
    if prod_url:
        print("Testing Production Database")
        print("-" * 70)
        prod_ok = test_connection(prod_url, "Production DB")
        print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Development DB: {'✅ PASS' if dev_ok else '❌ FAIL'}")
    if prod_url:
        print(f"Production DB:  {'✅ PASS' if prod_ok else '❌ FAIL'}")
    else:
        print(f"Production DB:  ⊘ SKIPPED (not configured)")
    print()
    
    # Exit code
    if not dev_ok or (prod_url and not prod_ok):
        print("❌ Some database connections failed")
        return 1
    else:
        print("✅ All configured databases are accessible")
        return 0


if __name__ == "__main__":
    sys.exit(main())
