from typing import Optional
import aiohttp
import logging

from app.db.connection import db
from scrapers.animes import fetch_and_insert_anime_data

logger = logging.getLogger(__name__)


class AnimeDownloadService:
    @staticmethod
    async def find_or_download_anime(
        anime_name: str, 
        mal_id: Optional[int] = None,
        anime_url: Optional[str] = None
    ) -> Optional[dict]:
        """
        Find anime in database or download it if missing.
        Priority: MAL ID > anime name exact match > URL scraping
        """
        try:
            # Try to find by MAL ID first
            if mal_id:
                existing_anime = db.get_records("anime", {"mal_id": mal_id})
                if existing_anime:
                    return existing_anime[0]
            
            # Try to find by exact name match
            existing_anime = db.get_records("anime", {"name": anime_name})
            if existing_anime:
                return existing_anime[0]
            
            # If URL provided, try to scrape
            if anime_url:
                logger.info(f"🔄 Downloading anime data for: {anime_name}")
                
                async with aiohttp.ClientSession() as session:
                    anime_model = await fetch_and_insert_anime_data(session, anime_url)
                    
                    if anime_model and hasattr(anime_model, 'id') and anime_model.id:
                        downloaded_anime = db.get_record_by_id("anime", anime_model.id)
                        if downloaded_anime:
                            logger.info(f"✅ Successfully downloaded: {anime_name}")
                            return downloaded_anime
            
            # Create a basic anime record if all else fails
            logger.info(f"📝 Creating basic anime record for: {anime_name}")
            anime_data = {
                "name": anime_name,
                "mal_id": mal_id
            }
            
            created_anime = db.insert_record("anime", anime_data)
            if created_anime:
                logger.info(f"✅ Created basic anime record: {anime_name}")
                return created_anime
            
            logger.error(f"❌ Failed to create anime record for: {anime_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in find_or_download_anime for {anime_name}: {str(e)}")
            return None
    
    @staticmethod
    async def auto_download_missing_anime(user_anime_list: list) -> int:
        """
        Auto-download any missing anime from a user's MAL list
        Returns count of successfully downloaded anime
        """
        downloaded_count = 0
        
        for anime_item in user_anime_list:
            try:
                anime_data = anime_item["node"]
                mal_id = anime_data["id"]
                anime_name = anime_data["title"]
                
                # Check if anime exists
                existing = db.get_records("anime", {"mal_id": mal_id})
                
                if not existing:
                    # Try to construct MAL URL for scraping
                    mal_url = f"https://myanimelist.net/anime/{mal_id}"
                    
                    result = await AnimeDownloadService.find_or_download_anime(
                        anime_name=anime_name,
                        mal_id=mal_id,
                        anime_url=mal_url
                    )
                    
                    if result:
                        downloaded_count += 1
                        
            except Exception as e:
                logger.error(f"❌ Error auto-downloading anime: {str(e)}")
                continue
        
        logger.info(f"🎯 Auto-downloaded {downloaded_count} missing anime")
        return downloaded_count