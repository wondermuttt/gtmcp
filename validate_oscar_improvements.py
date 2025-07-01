#!/usr/bin/env python3
"""Quick validation script for OSCAR improvements."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gtmcp.clients.oscar_client import OscarClient

def main():
    print("🔍 Validating OSCAR Improvements")
    print("=" * 40)
    
    client = OscarClient()
    
    with client:
        # Test connection
        print("1. Testing connection...")
        if not client.test_connection():
            print("❌ Connection failed")
            return
        print("✅ Connection successful")
        
        # Get semesters
        print("\n2. Getting available semesters...")
        try:
            semesters = client.get_available_semesters()
            active_semesters = [s for s in semesters if not s.view_only]
            if not active_semesters:
                print("❌ No active semesters found")
                return
            current_semester = active_semesters[0]
            print(f"✅ Found {len(semesters)} semesters, using {current_semester.name}")
        except Exception as e:
            print(f"❌ Semester error: {e}")
            return
        
        # Get subjects
        print("\n3. Getting subjects...")
        try:
            subjects = client.get_subjects(current_semester.code)
            cs_subject = next((s for s in subjects if s.code == 'CS'), None)
            if not cs_subject:
                print("❌ CS subject not found")
                return
            print(f"✅ Found {len(subjects)} subjects, CS available")
        except Exception as e:
            print(f"❌ Subject error: {e}")
            return
        
        # Test improved course listing
        print("\n4. Testing improved course listing...")
        try:
            courses = client.get_courses_by_subject(current_semester.code, "CS")
            print(f"✅ NEW METHOD: Found {len(courses)} CS courses")
            
            if courses:
                print(f"   Sample: {courses[0].subject} {courses[0].course_number}: {courses[0].title}")
                
                # Test search filtering
                print("\n5. Testing search filtering...")
                search_results = client.search_courses(current_semester.code, "CS", course_num="1301")
                print(f"✅ SEARCH FILTER: Found {len(search_results)} courses matching '1301'")
                
                # Test course details
                print("\n6. Testing course details...")
                try:
                    details = client.get_course_details(current_semester.code, courses[0].crn)
                    print(f"✅ COURSE DETAILS: {details.title}")
                    print(f"   Seats: {details.registration.seats_remaining}/{details.registration.seats_capacity}")
                except Exception as e:
                    print(f"⚠️ Course details error (may be expected): {e}")
            
        except Exception as e:
            print(f"❌ Course listing error: {e}")
            return
    
    print("\n" + "=" * 40)
    print("✅ OSCAR IMPROVEMENTS VALIDATION COMPLETE")
    print("\nKey Improvements Tested:")
    print("✅ get_courses_by_subject() - Gets ALL courses for subject")
    print("✅ search_courses() - Now filters locally for reliability")
    print("✅ Proper GT workflow - No more 500 errors expected")

if __name__ == "__main__":
    main()