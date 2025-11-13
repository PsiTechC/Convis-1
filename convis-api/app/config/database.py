from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure
from .settings import settings
import logging
import os

logger = logging.getLogger(__name__)

class Database:
    client = None
    db = None

    @classmethod
    def connect(cls):
        """Connect to MongoDB"""
        if cls.client is None:
            try:
                # Force use of Google DNS for DNS resolution
                import dns.resolver
                dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
                dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']

                # Production-ready configuration for 1000+ concurrent users
                cls.client = MongoClient(
                    settings.mongodb_uri,
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=20000,
                    socketTimeoutMS=45000,  # Increased for long-running queries
                    retryWrites=True,
                    retryReads=True,
                    maxPoolSize=200,  # Increased for high concurrency
                    minPoolSize=10,  # Keep connections warm
                    maxIdleTimeMS=45000,  # Close idle connections
                    waitQueueTimeoutMS=10000,  # Max wait for available connection
                )
                # Test the connection
                cls.client.admin.command('ping')
                cls.db = cls.client[settings.database_name]
                logger.info("Successfully connected to MongoDB")
            except ConfigurationError as e:
                logger.error(f"MongoDB Configuration Error: {e}")
                logger.error("Please check your MongoDB connection string in .env file")
                logger.error("The MongoDB cluster might not exist or DNS cannot resolve the hostname")
                raise
            except ConnectionFailure as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                raise
        return cls.db

    @classmethod
    def get_db(cls):
        """Get database instance"""
        if cls.db is None:
            cls.connect()
        return cls.db

    @classmethod
    def close(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
