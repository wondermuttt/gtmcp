# Filter Issues and Fix Plan

## Issues Identified from ChatGPT Testing

### 1. OMSCS Filter Including Undergraduate Courses
**Problem**: OMSCS filter returns CS 2110, CS 2698, CS 2699 (all < 6000)
**Root Cause**: Filter only checks section pattern (O01-O03) without course level
**Fix**: Add graduate-level filtering (course number >= 6000) for OMS programs

### 2. OMSA/OMSCyber Missing Non-CS Departments  
**Problem**: OMSA doesn't return ISYE/MATH courses; OMSCyber missing PUBP/ECE
**Root Cause**: Our test shows OMSA+ISYE works, but ChatGPT says it doesn't - needs investigation
**Fix**: Verify cross-department functionality

### 3. Atlanta Filter Including Online Sections
**Problem**: ChatGPT reports OAN sections appearing in Atlanta results
**Root Cause**: Campus filter might not be excluding all online sections
**Fix**: Ensure campus='A' filter excludes ALL O-prefix sections

### 4. Lorraine Campus Code Wrong
**Problem**: Lorraine filter uses campus='R' but should be 'L'
**Root Cause**: Incorrect mapping in PROGRAM_FILTERS
**Fix**: Change lorraine campus code from 'R' to 'L'

### 5. Shenzhen Not Capturing OSZ
**Problem**: Shenzhen filter missing OSZ (Online Shenzhen) sections
**Root Cause**: Filter only checks campus code, not section patterns
**Fix**: Add section pattern matching for Shenzhen (OSZ, possibly S-prefix)

### 6. Professional Filter Not Working
**Problem**: Q-prefix sections (QSA, QCH) not returned
**Root Cause**: Professional filter maps to P-prefix, not Q-prefix
**Fix**: Change professional sections from P/PE/PRO to Q-prefix pattern

### 7. VIP Filter (Partially Working)
**Problem**: VIP subject courses work, but filter might miss some
**Root Cause**: Filter correctly captures VP sections
**Fix**: Ensure VIP subject courses are included

## Test-Driven Development Plan

### Step 1: Write Comprehensive Unit Tests
Create tests for each filter that verify:
- Correct sections/campus codes included
- Incorrect sections/campus codes excluded  
- Graduate level filtering where applicable
- Cross-department functionality

### Step 2: Fix Mappings
Update PROGRAM_FILTERS with correct codes:
- Lorraine: 'L' not 'R'
- Professional: Q-prefix not P-prefix
- Shenzhen: Add section patterns

### Step 3: Add Level Filtering
For OMS programs, add course level check:
- Only include courses >= 6000
- Keep section filtering as secondary check

### Step 4: Enhance Campus Filters
For campus-based filters:
- Ensure they exclude conflicting sections
- Atlanta should exclude all O-prefix
- Online should exclude all non-O-prefix

### Step 5: Integration Testing
Run full test suite including ChatGPT's test cases

## Implementation Order
1. Fix simple mapping errors (Lorraine, Professional)
2. Add Shenzhen section patterns
3. Implement graduate-level filtering for OMS
4. Enhance campus filter exclusions
5. Verify cross-department functionality