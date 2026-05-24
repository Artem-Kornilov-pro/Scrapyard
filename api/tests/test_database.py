import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from api.core.database import connect_to_mongo, close_mongo_connection, db


@pytest.fixture
def mock_motor():
    """Mock Motor client for testing."""
    with patch("api.core.database.AsyncIOMotorClient") as mock:
        mock_client = MagicMock()
        mock_db = MagicMock()
        
        # Setup collections
        mock_collection = MagicMock()
        mock_collection.create_index = AsyncMock()
        mock_db.scraping_jobs = mock_collection
        mock_db.scraped_results = mock_collection
        
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock.return_value = mock_client
        
        yield mock


@pytest.mark.asyncio
async def test_connect_to_mongo(mock_motor):
    """Test MongoDB connection and index creation."""
    await connect_to_mongo()
    
    # Check client was created
    mock_motor.assert_called_once()
    
    # Check indexes were created
    collection = db.db.scraping_jobs
    assert collection.create_index.call_count >= 4


@pytest.mark.asyncio
async def test_close_mongo_connection():
    """Test closing MongoDB connection."""
    # Setup mock client
    mock_client = MagicMock()
    mock_client.close = MagicMock()
    db.client = mock_client
    
    await close_mongo_connection()
    
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_mongo_connection_no_client():
    """Test closing when client doesn't exist."""
    db.client = None
    await close_mongo_connection()  # Should not raise