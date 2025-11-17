"""
Test filename sanitizer
"""

from app.utils.filename_sanitizer import sanitize_filename, generate_unique_filename

# Test cases
test_filenames = [
    "To Be Hero X Theme Song Full   New Type of Hero - Sub Español  AMV  - El Cóndor Anime - コンドル (1080p, h264).mp4",
    "My File (2024).pdf",
    "Español ñ.txt",
    "コンドル.mp4",
    "file with spaces.jpg",
    "special!@#$%chars.png",
    "normal_file.txt",
    "UPPERCASE.PDF",
]

print("=" * 80)
print("Filename Sanitizer Tests")
print("=" * 80)

for original in test_filenames:
    sanitized = sanitize_filename(original)
    unique = generate_unique_filename(original, "abc12345")
    
    print(f"\nOriginal:  {original}")
    print(f"Sanitized: {sanitized}")
    print(f"Unique:    {unique}")
    print("-" * 80)

print("\n✅ All tests completed!")
