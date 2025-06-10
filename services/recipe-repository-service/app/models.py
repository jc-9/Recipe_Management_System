from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import datetime

# Base class for declarative models
Base = declarative_base()

class RecipeBook(Base):
    __tablename__ = "recipe_books"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    # Semantic Versioning parts
    major_version = Column(Integer, nullable=False, default=1)
    minor_version = Column(Integer, nullable=False, default=0)
    patch_version = Column(Integer, nullable=False, default=0) # Auto-managed by system
    # Ensure uniqueness of (name, major_version, minor_version, patch_version)
    __table_args__ = (UniqueConstraint('name', 'major_version', 'minor_version', 'patch_version', name='_recipe_book_version_uc'),)

    status = Column(String, default="DRAFT", nullable=False) # e.g., DRAFT, APPROVED, RELEASED, ARCHIVED
    release_date = Column(DateTime(timezone=True), default=None, nullable=True) # Set upon RELEASED status
    author = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    recipes = relationship("Recipe", back_populates="recipe_book", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RecipeBook(id={self.id}, name='{self.name}', version='{self.full_version}', status='{self.status}')>"

    @property
    def full_version(self):
        return f"{self.major_version}.{self.minor_version}.{self.patch_version}"

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    recipe_book_id = Column(Integer, ForeignKey("recipe_books.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    product_number = Column(String, index=True, nullable=False) # e.g., 'XYZ-1234'
    # Version of the individual recipe within the book (e.g., specific to the product number)
    # This can be simple or semantic, depending on granularity needed. Let's start simple.
    recipe_version = Column(String, default="1.0", nullable=False)
    instructions = Column(Text, nullable=True) # Could be JSON or just text instructions
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    recipe_book = relationship("RecipeBook", back_populates="recipes")
    software_components = relationship("SoftwareComponent", back_populates="recipe", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Recipe(id={self.id}, name='{self.name}', product_number='{self.product_number}')>"

class SoftwareComponent(Base):
    __tablename__ = "software_components"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    component_type = Column(String, nullable=False) # e.g., 'robot_firmware', 'camera_config', 'plc_program', 'shared_library'
    minio_object_key = Column(String, unique=True, index=True, nullable=False) # Path/key in MinIO
    checksum = Column(String(64), nullable=False) # e.g., SHA256 hash (64 chars)
    original_filename = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    recipe = relationship("Recipe", back_populates="software_components")

    def __repr__(self):
        return f"<SoftwareComponent(id={self.id}, type='{self.component_type}', key='{self.minio_object_key}')>"