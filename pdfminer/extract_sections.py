"""
PDF Section Extractor
Extracts sections and tables from SDVoE API Reference Guide PDF into individual markdown files.
"""

import re
import os
import shutil
import argparse
from pathlib import Path
import pymupdf  # PyMuPDF (fitz)
from typing import Dict, List, Tuple, Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PDF_PATH = SCRIPT_DIR / "PDS-062489_SDVoE_Developers_API_Reference_Guide_rev3p8.pdf"
TOC_PATH = SCRIPT_DIR / "Table of Contents.md"
OUTPUT_DIR = SCRIPT_DIR / "docs"
TABLES_DIR = SCRIPT_DIR / "docs" / "tables"


def parse_toc(toc_path: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse the Table of Contents markdown file to extract sections and tables.
    
    Returns:
        Tuple of (sections_list, tables_list)
    """
    with open(toc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = []
    tables = []
    
    # Split into main ToC and List of Tables
    parts = content.split('### List of Tables')
    toc_content = parts[0]
    tables_content = parts[1] if len(parts) > 1 else ""
    
    # Parse sections from ToC
    # Pattern: section_number SECTION_TITLE .. page_number
    section_pattern = r'^([\dA-Z]+(?:\.\d+)*)\s+(.+?)\s*\.{2,}\s*(\d+)'
    
    for line in toc_content.split('\n'):
        match = re.match(section_pattern, line.strip())
        if match:
            section_num = match.group(1)
            title = match.group(2).strip()
            page = int(match.group(3))
            
            sections.append({
                'number': section_num,
                'title': title,
                'page': page,
                'level': section_num.count('.')
            })
    
    # Parse tables from List of Tables
    # Pattern: TABLE X: TABLE_TITLE..page_number
    table_pattern = r'^TABLE\s+(\d+):\s+(.+?)\s*\.{2,}\s*(\d+)'
    
    for line in tables_content.split('\n'):
        match = re.match(table_pattern, line.strip())
        if match:
            table_num = int(match.group(1))
            title = match.group(2).strip()
            page = int(match.group(3))
            
            tables.append({
                'number': table_num,
                'title': title,
                'page': page
            })
    
    return sections, tables


def group_sections_by_major(sections: List[Dict]) -> Dict[str, Dict]:
    """
    Group sections by their major section numbers.
    For example, 4.1, 4.2, 4.3 all belong to different files.
    
    Returns:
        Dict mapping major section (e.g., '4.1') to section info including page range
    """
    grouped = {}
    
    # Sort sections by page number
    sorted_sections = sorted(sections, key=lambda x: x['page'])
    
    for i, section in enumerate(sorted_sections):
        section_num = section['number']
        
        # Determine the grouping key
        if section_num.startswith('A.'):
            # Appendix sections - group by A.1, A.2, etc.
            key = section_num
        elif '.' in section_num:
            # Subsection - for section 4, 5, 6, 7, create files per second level
            parts = section_num.split('.')
            if len(parts) >= 2 and parts[0] in ['4', '5', '6', '7']:
                # Use two levels: 4.1, 4.2, etc.
                key = f"{parts[0]}.{parts[1]}"
            else:
                # Other subsections stay with parent
                key = parts[0]
        else:
            # Top-level section
            key = section_num
        
        # Initialize or update the group
        if key not in grouped:
            # Determine end page (start of next major section)
            end_page = None
            for j in range(i + 1, len(sorted_sections)):
                next_section = sorted_sections[j]
                next_num = next_section['number']
                
                # Check if this is a different major section
                if next_num.startswith('A.'):
                    next_key = next_num
                elif '.' in next_num:
                    parts = next_num.split('.')
                    if len(parts) >= 2 and parts[0] in ['4', '5', '6', '7']:
                        next_key = f"{parts[0]}.{parts[1]}"
                    else:
                        next_key = parts[0]
                else:
                    next_key = next_num
                
                if next_key != key:
                    end_page = next_section['page'] - 1
                    break
            
            grouped[key] = {
                'number': key,
                'title': section['title'],
                'start_page': section['page'],
                'end_page': end_page,  # Will be None for the last section
                'subsections': []
            }
        
        # Add as subsection if it's not the main section
        if section_num != key:
            grouped[key]['subsections'].append(section)
    
    return grouped


def extract_text_from_pages(pdf_path: str, start_page: int, end_page: Optional[int]) -> str:
    """
    Extract text from specified page range.
    
    Args:
        pdf_path: Path to PDF file
        start_page: Starting page number (1-indexed as in PDF)
        end_page: Ending page number (1-indexed), or None for last page
    
    Returns:
        Extracted text content
    """
    doc = pymupdf.open(pdf_path)
    content = []
    
    # Convert to 0-indexed
    start_idx = start_page - 1
    end_idx = (end_page - 1) if end_page else (len(doc) - 1)
    
    for page_num in range(start_idx, end_idx + 1):
        page = doc[page_num]
        text = page.get_text()
        content.append(text)
    
    doc.close()
    
    return '\n'.join(content)


def remove_content_before_section(text: str, section_num: str, section_title: str) -> str:
    """
    Remove all content before the actual section starts.
    Finds the line starting with the section number and title.
    
    Args:
        text: Raw extracted text
        section_num: Section number (e.g., "4.9")
        section_title: Section title
    
    Returns:
        Text starting from the actual section
    """
    lines = text.split('\n')
    
    # Create patterns to match the section header
    # Try multiple variations
    patterns = [
        rf"^{re.escape(section_num)}\s+{re.escape(section_title)}\s*$",
        rf"^{re.escape(section_num)}\s+{re.escape(section_title.title())}\s*$",
        rf"^{re.escape(section_num)}\s+{re.escape(section_title.lower())}\s*$",
        rf"^{re.escape(section_num)}\s+{re.escape(section_title.upper())}\s*$",
        # Also try with "Command" normalized
        rf"^{re.escape(section_num)}\s+Command\s+",
        rf"^{re.escape(section_num)}\s+COMMAND\s+",
    ]
    
    # Find the first line that matches the section header
    start_index = 0
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        for pattern in patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                start_index = i
                break
        if start_index > 0:
            break
    
    # Return content from the section start onwards
    return '\n'.join(lines[start_index:])


def clean_extracted_text(text: str, section_number: str, section_title: str, subsections: List[Dict]) -> str:
    """
    Clean and format extracted text for markdown output.
    
    Args:
        text: Raw extracted text
        section_number: Section number (e.g., "4.9")
        section_title: Section title
        subsections: List of subsection dicts with 'number' and 'title' keys
    
    Returns:
        Cleaned markdown text
    """
    # Build subsection mapping for quick lookup
    subsection_map = {sub['number']: sub['title'] for sub in subsections}
    
    # First, remove content before the actual section
    text = remove_content_before_section(text, section_number, section_title)
    
    lines = text.split('\n')
    cleaned_lines = []
    
    # Enhanced header/footer patterns - more comprehensive
    header_footer_patterns = [
        r'^PDS-062489',
        r'^SDVoE Developers API',
        r'^Reference Guide',
        r'The information contained herein.*exclusive property',
        r'be distributed.*copied.*reproduced',
        r'written permission of Semtech',
        r'^Rev \d+\.\d+',
        r'^Page \d+ of \d+',
        r'Semtech Confidential',
        # Date patterns - any month and year
        r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*$',
        r'^\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*$',
        r'^\s*Tamas Takacs\s*$',
        r'^\s*Lightware\s*$',
        r'^\d{2}/\d{2}/\d{4}',
        # Partial footer text variations
        r'^be distributed.*$',
        r'^written permission.*$',
        r'.*exclusive property of Semtech.*',
    ]
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines initially (we'll add them back strategically)
        if not line_stripped:
            continue
        
        # Skip header/footer lines
        skip = False
        for pattern in header_footer_patterns:
            if re.search(pattern, line_stripped, re.IGNORECASE):
                skip = True
                break
        
        if not skip:
            cleaned_lines.append(line)
    
    # Convert subsection numbers to markdown headers using ToC as source of truth
    formatted_lines = []
    for line in cleaned_lines:
        line_stripped = line.strip()
        
        # Check if this line is a known subsection number from the ToC
        if line_stripped in subsection_map:
            # This is a subsection header - convert to markdown header with title from ToC
            subsection_num = line_stripped
            subsection_title = subsection_map[subsection_num]
            level = subsection_num.count('.')
            header_prefix = '#' * (level + 1)  # ## for 2-level, ### for 3-level, etc.
            formatted_lines.append(f"\n{header_prefix} {subsection_num} {subsection_title}\n")
        else:
            # Not a subsection number, keep as-is
            formatted_lines.append(line)
    
    content = '\n'.join(formatted_lines)
    
    # Reduce multiple consecutive blank lines to max 2
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Add main section header at the top
    markdown = f"# {section_number} {section_title}\n\n{content}"
    
    return markdown


def extract_tables_from_page(pdf_path: str, page_num: int, table_title: str) -> str:
    """
    Extract table from a specific page and convert to markdown format.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        table_title: Title of the table
    
    Returns:
        Markdown formatted table
    """
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]  # Convert to 0-indexed
    
    # Extract tables using PyMuPDF
    tables = page.find_tables()
    
    if not tables.tables:
        # No tables found, extract text instead
        text = page.get_text()
        doc.close()
        return f"# {table_title}\n\n{text}\n"
    
    markdown_output = f"# {table_title}\n\n"
    
    for table in tables:
        # Convert table to markdown
        table_data = table.extract()
        
        if not table_data:
            continue
        
        # Create markdown table
        # Header row
        if len(table_data) > 0:
            header = table_data[0]
            markdown_output += "| " + " | ".join(str(cell) if cell else "" for cell in header) + " |\n"
            markdown_output += "| " + " | ".join(["---"] * len(header)) + " |\n"
            
            # Data rows
            for row in table_data[1:]:
                markdown_output += "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |\n"
        
        markdown_output += "\n"
    
    doc.close()
    return markdown_output


def sanitize_filename(text: str) -> str:
    """Convert text to valid filename."""
    # Replace spaces and special chars with underscores
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '_', text)
    return text.upper()


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Extract sections and tables from PDF to markdown files')
    parser.add_argument('--clean', action='store_true', help='Delete docs/ directory before extraction')
    parser.add_argument('--max-files', type=int, help='Maximum number of section files to extract (for testing)')
    parser.add_argument('--max-tables', type=int, help='Maximum number of table files to extract (for testing)')
    args = parser.parse_args()
    
    print("Starting PDF extraction...")
    
    # Clean output directories if requested
    if args.clean:
        if OUTPUT_DIR.exists():
            print(f"Cleaning {OUTPUT_DIR}...")
            try:
                shutil.rmtree(OUTPUT_DIR)
            except PermissionError as e:
                print(f"Warning: Could not delete some files: {e}")
                print("Trying to delete individual files...")
                # Try to delete files individually
                for root, dirs, files in os.walk(OUTPUT_DIR, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except Exception:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except Exception:
                            pass
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TABLES_DIR, exist_ok=True)
    
    # Parse Table of Contents
    print("Parsing Table of Contents...")
    sections, tables = parse_toc(TOC_PATH)
    print(f"Found {len(sections)} sections and {len(tables)} tables")
    
    # Group sections
    print("Grouping sections...")
    grouped_sections = group_sections_by_major(sections)
    print(f"Created {len(grouped_sections)} section groups")
    
    # Apply max files limit if specified
    if args.max_files:
        print(f"Limiting to first {args.max_files} section files (testing mode)")
    
    # Extract each section
    print("\nExtracting sections...")
    section_count = 0
    for key in sorted(grouped_sections.keys(), key=lambda x: (
        0 if x[0].isdigit() else 1,  # Numbers first
        [int(p) if p.isdigit() else p for p in x.split('.')]  # Natural sort
    )):
        # Check max files limit
        if args.max_files and section_count >= args.max_files:
            print(f"\nReached max files limit ({args.max_files}), stopping section extraction")
            break
        
        section_info = grouped_sections[key]
        section_num = section_info['number']
        section_title = section_info['title']
        start_page = section_info['start_page']
        end_page = section_info['end_page']
        
        print(f"Extracting {section_num}: {section_title} (pages {start_page}-{end_page or 'end'})")
        
        # Extract text
        text = extract_text_from_pages(PDF_PATH, start_page, end_page)
        
        # Clean and format with subsections from ToC
        markdown_content = clean_extracted_text(text, section_num, section_title, section_info['subsections'])
        
        # Create filename
        safe_title = sanitize_filename(section_title)
        filename = f"section_{section_num.replace('.', '_')}_{safe_title}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"  → Created {filename}")
        section_count += 1
    
    # Apply max tables limit if specified
    if args.max_tables:
        print(f"\nLimiting to first {args.max_tables} table files (testing mode)")
    
    # Extract tables
    print("\nExtracting tables...")
    table_count = 0
    for table_info in tables:
        # Check max tables limit
        if args.max_tables and table_count >= args.max_tables:
            print(f"\nReached max tables limit ({args.max_tables}), stopping table extraction")
            break
        
        table_num = table_info['number']
        table_title = table_info['title']
        page = table_info['page']
        
        print(f"Extracting Table {table_num}: {table_title} (page {page})")
        
        # Extract table
        markdown_table = extract_tables_from_page(PDF_PATH, page, f"TABLE {table_num}: {table_title}")
        
        # Create filename
        safe_title = sanitize_filename(table_title)
        filename = f"table_{table_num}_{safe_title}.md"
        filepath = os.path.join(TABLES_DIR, filename)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_table)
        
        print(f"  → Created {filename}")
        table_count += 1
    
    print("\n✓ Extraction complete!")
    print(f"  Sections: {section_count} files in {OUTPUT_DIR}/")
    print(f"  Tables: {table_count} files in {TABLES_DIR}/")


if __name__ == "__main__":
    main()
