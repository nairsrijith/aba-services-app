#!/usr/bin/env python
"""
Migration script to clean up existing activities and designations by removing leading/trailing whitespace.
This should be run once after deploying the whitespace trimming fix.

Usage: python cleanup_whitespace.py
Or in Docker: docker exec <container_name> python cleanup_whitespace.py
"""
import sys
import os

# Change to app directory if needed
if os.path.exists('/myapp'):
    os.chdir('/myapp')
    sys.path.insert(0, '/myapp')

try:
    from app import create_app, db
    from app.models import Activity, Designation
    
    app = create_app()
    with app.app_context():
        print("Starting cleanup of activities and designations...")
        
        # Cleanup activities
        activities = Activity.query.all()
        activities_updated = 0
        
        for activity in activities:
            original_name = activity.activity_name
            stripped_name = original_name.strip()
            
            if original_name != stripped_name:
                print(f"Updating activity: '{original_name}' → '{stripped_name}'")
                activity.activity_name = stripped_name
                activities_updated += 1
        
        # Cleanup designations
        designations = Designation.query.all()
        designations_updated = 0
        
        for designation in designations:
            original_name = designation.designation
            stripped_name = original_name.strip()
            
            if original_name != stripped_name:
                print(f"Updating designation: '{original_name}' → '{stripped_name}'")
                designation.designation = stripped_name
                designations_updated += 1
        
        if activities_updated > 0 or designations_updated > 0:
            db.session.commit()
            print(f"\n✓ Cleanup complete!")
            print(f"  - Activities updated: {activities_updated}")
            print(f"  - Designations updated: {designations_updated}")
        else:
            print("✓ No records with trailing/leading whitespace found.")
        
except Exception as e:
    print(f"Error during cleanup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
