#!/usr/bin/env python3
"""
Simple debug script to test Supabase insertions with your actual scraper data.
Run this to see the exact 400 error details.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv('.env.backend')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Test data that matches your scraper output
test_anime_data = {
    'name': 'Test Anime',
    'english_title': 'Test Anime',
    'japanese_title': 'テストアニメ',
    'episodes': '12',
    'status': 'Finished Airing',
    'aired': 'Jan 2023 to Mar 2023',
    'source': 'Manga',
    'genres': 'Action, Comedy',
    'themes': 'School',
    'duration': '24 min per ep',
    'rating': 'PG-13',
    'score': '8.5',
    'ranked': '#100',
    'popularity': '#50',
    'synopsis': 'A test anime synopsis...',
    'created_at': datetime.now().isoformat(),
    'updated_at': datetime.now().isoformat()
}

print('🔍 Testing anime insertion...')
try:
    result = supabase.table('anime').insert(test_anime_data).execute()
    print(f'✅ Success! ID: {result.data[0]["id"]}')
    anime_id = result.data[0]["id"]
    
    # Test character insertion
    test_character_data = {
        'name': 'Test Character',
        'photo': 'https://example.com/photo.jpg',
        'anime_id': anime_id,
        'created_at': datetime.now().isoformat()
    }
    
    print('🔍 Testing character insertion...')
    char_result = supabase.table('characters').insert(test_character_data).execute()
    print(f'✅ Character success! ID: {char_result.data[0]["id"]}')
    
except Exception as e:
    print(f'❌ Error: {e}')
    print('\n💡 This shows the exact validation error!')