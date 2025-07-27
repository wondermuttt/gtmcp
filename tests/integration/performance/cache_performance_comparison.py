#!/usr/bin/env python3
"""Compare performance of old JSON cache vs new pickle_gz cache"""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, '/home/wondermutt/gtmcp/src')

from gtmcp.fast_cache import FastCache
from gtmcp.models import CourseInfo
from datetime import datetime

print("Cache Performance Comparison: JSON vs Pickle+Gzip")
print("=" * 60)

# Create realistic test data (simulate full cache)
def create_full_cache():
    cache = {}
    timestamps = {}
    
    # Semesters
    cache['available_semesters'] = [{
        'code': f'20{25-i}{m:02d}',
        'name': f'Term {i}',
        'view_only': False,
        '__type__': 'Semester'
    } for i in range(3) for m in [2, 5, 8]]
    
    # Course lists (bulk of data)
    for term in ['202508', '202505', '202502']:
        for subject in ['CS', 'CSE', 'ECE', 'MATH', 'ISYE']:
            key = f'{term}_{subject}_all'
            cache[key] = [{
                'crn': str(20000 + i),
                'title': f'{subject} {6000+i}: Long Course Title with Description of Advanced Topics in {subject}',
                'subject': subject,
                'course_number': str(6000 + i),
                'section': chr(65 + (i % 26)),
                '__type__': 'CourseInfo'
            } for i in range(300)]  # 300 courses per subject
            timestamps[key] = datetime.now().isoformat()
    
    # Individual course entries (1000+)
    for i in range(1500):
        key = f'course_202508_{10000+i}'
        cache[key] = {
            'course': {
                'crn': str(10000 + i),
                'title': 'Very Long Course Title to Simulate Real Data',
                'subject': 'CS',
                'course_number': str(6000 + i),
                'section': 'A',
                '__type__': 'CourseInfo'
            },
            'term_code': '202508',
            'type': 'course'
        }
        timestamps[key] = datetime.now().isoformat()
    
    return {'cache': cache, 'timestamps': timestamps}

print("Creating test data...")
test_data = create_full_cache()
total_entries = len(test_data['cache'])
course_count = sum(len(v) if isinstance(v, list) else 0 for v in test_data['cache'].values())
print(f"Total cache entries: {total_entries}")
print(f"Total courses: {course_count}")

# Test old JSON approach
print("\n1. OLD APPROACH (JSON with indent):")
start_total = time.time()

# Save
start = time.time()
json_str = json.dumps(test_data, indent=2)
json_save_time = time.time() - start

with open('/tmp/cache_json.json', 'w') as f:
    f.write(json_str)
json_size = Path('/tmp/cache_json.json').stat().st_size

# Load
start = time.time()
with open('/tmp/cache_json.json', 'r') as f:
    loaded = json.load(f)
json_load_time = time.time() - start

json_total_time = time.time() - start_total

print(f"  Save time: {json_save_time:.3f}s")
print(f"  Load time: {json_load_time:.3f}s")
print(f"  Total time: {json_total_time:.3f}s")
print(f"  File size: {json_size/1024/1024:.2f} MB")

# Test new pickle_gz approach
print("\n2. NEW APPROACH (Pickle + Gzip):")
cache_dir = Path('/tmp/test_cache_perf')
cache_dir.mkdir(exist_ok=True)

fast_cache = FastCache(cache_dir, backend='pickle_gz')
start_total = time.time()

# Save
start = time.time()
fast_cache.save(test_data)
pickle_save_time = time.time() - start

# Load
start = time.time()
loaded = fast_cache.load()
pickle_load_time = time.time() - start

pickle_total_time = time.time() - start_total

stats = fast_cache.get_stats()
pickle_size = stats['size_mb'] * 1024 * 1024

print(f"  Save time: {pickle_save_time:.3f}s")
print(f"  Load time: {pickle_load_time:.3f}s") 
print(f"  Total time: {pickle_total_time:.3f}s")
print(f"  File size: {stats['size_mb']:.2f} MB")

# Calculate improvements
print("\n3. PERFORMANCE IMPROVEMENTS:")
print("=" * 60)
save_speedup = json_save_time / pickle_save_time
load_speedup = json_load_time / pickle_load_time
total_speedup = json_total_time / pickle_total_time
size_reduction = (1 - pickle_size/json_size) * 100

print(f"  Save: {save_speedup:.1f}x faster")
print(f"  Load: {load_speedup:.1f}x faster")
print(f"  Total: {total_speedup:.1f}x faster")
print(f"  Size: {size_reduction:.1f}% smaller")

print(f"\n  Time saved per operation: {json_total_time - pickle_total_time:.3f}s")
print(f"  Space saved: {(json_size - pickle_size)/1024/1024:.2f} MB")

# Clean up
import os
os.remove('/tmp/cache_json.json')
import shutil
shutil.rmtree(cache_dir)

print("\n4. CONCLUSION:")
print("=" * 60)
print(f"For a cache with {total_entries} entries and {course_count} courses:")
print(f"- Old JSON approach: {json_total_time:.3f}s, {json_size/1024/1024:.2f} MB")
print(f"- New Pickle+Gzip: {pickle_total_time:.3f}s, {stats['size_mb']:.2f} MB")
print(f"\nThe new approach is {total_speedup:.1f}x faster and {size_reduction:.0f}% smaller!")
print("\nThis means ChatGPT will experience much faster response times,")
print("especially for repeated queries that benefit from caching.")