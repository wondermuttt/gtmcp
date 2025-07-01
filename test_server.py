#!/usr/bin/env python3
"""Test script for the Georgia Tech MCP Server."""

import asyncio
import json
from src.gtmcp.scraper import GTOscarScraper


async def test_scraper():
    """Test the scraper functionality."""
    print("Testing Georgia Tech OSCAR Scraper...")
    
    scraper = GTOscarScraper(delay=0.5)
    
    try:
        # Test 1: Get available semesters
        print("\n1. Testing get_available_semesters...")
        semesters = scraper.get_available_semesters()
        print(f"Found {len(semesters)} semesters")
        for sem in semesters[:5]:  # Show first 5
            print(f"  - {sem.name} ({sem.code}) {'[View Only]' if sem.view_only else ''}")
        
        # Find a current semester for testing
        current_semester = None
        for sem in semesters:
            if not sem.view_only and "2025" in sem.name:
                current_semester = sem
                break
                
        if not current_semester:
            print("No current semester found for testing")
            return
            
        print(f"\nUsing semester: {current_semester.name} ({current_semester.code})")
        
        # Test 2: Get subjects
        print("\n2. Testing get_subjects...")
        subjects = scraper.get_subjects(current_semester.code)
        print(f"Found {len(subjects)} subjects")
        for subj in subjects[:10]:  # Show first 10
            print(f"  - {subj.code}: {subj.name}")
        
        # Test 3: Search for CS courses
        print("\n3. Testing search_courses (CS)...")
        cs_courses = scraper.search_courses(current_semester.code, "CS")
        print(f"Found {len(cs_courses)} CS courses")
        for course in cs_courses[:5]:  # Show first 5
            print(f"  - {course.subject} {course.course_number}-{course.section}: {course.title} (CRN: {course.crn})")
        
        if cs_courses:
            # Test 4: Get course details
            test_course = cs_courses[0]
            print(f"\n4. Testing get_course_details for {test_course.subject} {test_course.course_number}...")
            details = scraper.get_course_details(current_semester.code, test_course.crn)
            
            print(f"Course: {details.title}")
            print(f"Credits: {details.credits}")
            print(f"Schedule Type: {details.schedule_type}")
            print(f"Campus: {details.campus}")
            print(f"Levels: {', '.join(details.levels)}")
            print(f"Seats: {details.registration.seats_actual}/{details.registration.seats_capacity} ({details.registration.seats_remaining} remaining)")
            print(f"Waitlist: {details.registration.waitlist_actual}/{details.registration.waitlist_capacity} ({details.registration.waitlist_remaining} remaining)")
            
            if details.restrictions:
                print(f"Restrictions: {len(details.restrictions)} found")
                for restriction in details.restrictions[:3]:
                    print(f"  - {restriction}")
            
            if details.catalog_url:
                print(f"Catalog URL: {details.catalog_url}")
        
        print("\n✅ All scraper tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_scraper())