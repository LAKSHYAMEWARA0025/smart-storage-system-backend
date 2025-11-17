# Media Upload Enhancements

## Overview

Enhanced media upload system with automatic metadata extraction, deduplication, and advanced filtering capabilities.

## New Features

### 1. Enhanced Metadata Extraction

#### For Images:
- **Dimensions**: Width, height, aspect ratio
- **Format**: Image format (JPEG, PNG, etc.)
- **EXIF Data**: Camera info, orientation, datetime (if available)

#### For Videos:
- **Duration**: Video length in seconds
- **Dimensions**: Width, height, aspect ratio
- **Codec**: Video codec information
- **Frame Rate**: FPS
- **Bitrate**: Video bitrate
- **Audio**: Audio codec, sample rate, channels

#### For All Files:
- **File Hash**: SHA-256 hash for deduplication
- **Original Filename**: Preserved original name
- **File Size**: Size in bytes
- **Category**: Auto-categorized (images, videos, documents, etc.)
- **Tags**: User-defined tags
- **Description**: User-provided description

### 2. File Deduplication

Files are automatically deduplicated based on SHA-256 hash. If you upload the same file twice, the system returns the existing file URL instead of creating a duplicate.

### 3. New API Endpoints

#### Upload with Metadata
```http
POST /api/files/upload
Content-Type: multipart/form-data

file: [binary]
tags: "vacation,beach,2024" (optional)
description: "Summer vacation photos" (optional)
```

**Response:**
```json
{
  "user_id": "uuid",
  "filename": "photo.jpg",
  "url": "https://...",
  "file_type": "image",
  "extension": ".jpg",
  "file_hash": "abc123...",
  "file_size": 1024000,
  "category": "images",
  "metadata": {
    "original_filename": "photo.jpg",
    "dimensions": {
      "width": 1920,
      "height": 1080,
      "aspect_ratio": 1.78
    },
    "tags": ["vacation", "beach", "2024"],
    "description": "Summer vacation photos"
  }
}
```

#### Get File Categories
```http
GET /api/files/categories
Authorization: Bearer <token>
```

**Response:**
```json
{
  "categories": [
    {
      "name": "images",
      "count": 45,
      "extensions": [".jpg", ".png", ".gif"]
    },
    {
      "name": "videos",
      "count": 12,
      "extensions": [".mp4", ".mov"]
    },
    {
      "name": "documents",
      "count": 8,
      "extensions": [".pdf", ".docx"]
    }
  ]
}
```

#### Get Files by Category
```http
GET /api/files/by-category?categories=images,videos
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total": 57,
  "categories": ["images", "videos"],
  "files": [
    {
      "id": "uuid",
      "filename": "photo.jpg",
      "url": "https://...",
      "category": "images",
      "file_size": 1024000,
      "metadata": {
        "dimensions": {"width": 1920, "height": 1080},
        "tags": ["vacation"],
        "description": "Beach photo"
      },
      "created_at": "2024-11-16T..."
    }
  ]
}
```

## File Categories

Files are automatically categorized based on extension:

- **images**: .jpg, .jpeg, .png, .gif, .webp, .svg, .bmp, .ico, .tiff
- **videos**: .mp4, .mov, .avi, .mkv, .webm, .flv, .wmv, .m4v
- **documents**: .pdf, .doc, .docx, .txt, .rtf, .odt
- **spreadsheets**: .xls, .xlsx, .csv, .ods
- **presentations**: .ppt, .pptx, .odp
- **audio**: .mp3, .wav, .ogg, .m4a, .flac, .aac, .wma
- **archives**: .zip, .rar, .7z, .tar, .gz, .bz2
- **code**: .py, .js, .html, .css, .java, .cpp, .c, .json, .xml
- **other**: Everything else

## Database Schema Updates

Run the migration in Supabase SQL Editor:

```sql
-- See: supabase_migrations/add_enhanced_metadata.sql
```

New columns added to `files` table:
- `file_hash` (VARCHAR): SHA-256 hash for deduplication
- `file_size` (BIGINT): File size in bytes
- `category` (VARCHAR): File category
- `metadata` (JSONB): Enhanced metadata object

## Installation

### 1. Install Dependencies

```bash
pip install Pillow==10.1.0 ffmpeg-python==0.2.0
```

### 2. Install FFmpeg (for video metadata)

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

### 3. Run Database Migration

Go to Supabase Dashboard → SQL Editor → Run the migration from `supabase_migrations/add_enhanced_metadata.sql`

## Usage Examples

### Upload Image with Tags
```python
import requests

files = {'file': open('photo.jpg', 'rb')}
data = {
    'tags': 'vacation,beach,summer',
    'description': 'Beautiful sunset at the beach'
}
headers = {'Authorization': 'Bearer YOUR_TOKEN'}

response = requests.post(
    'http://localhost:8000/api/files/upload',
    files=files,
    data=data,
    headers=headers
)
```

### Get All Categories
```python
response = requests.get(
    'http://localhost:8000/api/files/categories',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
categories = response.json()['categories']
```

### Filter by Multiple Categories
```python
response = requests.get(
    'http://localhost:8000/api/files/by-category?categories=images,videos',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
files = response.json()['files']
```

## Performance

- **Caching**: All endpoints use Redis caching (1 hour TTL)
- **Deduplication**: Prevents duplicate uploads, saves storage
- **Indexes**: Database indexes on `file_hash` and `category` for fast queries

## Notes

- Video metadata extraction requires FFmpeg to be installed
- Large video files may take a few seconds to process
- File hash calculation is done in-memory (suitable for files up to 50MB)
- Metadata is stored both in Supabase Storage and the database for redundancy
