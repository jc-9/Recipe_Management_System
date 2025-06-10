from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse # For file downloads later
import io # For handling file streams
import hashlib # For checksum calculation
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from botocore.exceptions import ClientError
import boto3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Recipe Repository Service",
    description="Manages recipe metadata and links to binary files in MinIO.",
    version="0.1.0"
)

# --- Database Configuration (PostgreSQL) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devuser:devpassword@db:5432/recipe_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    try:
        db = SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")
    #Provides a database session for the request lifecycle.

    try:
        yield db
    finally:
        if db.is_active:
            db.close()
    try:
        yield db
    finally:
        db.close()

# --- MinIO Configuration ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == 'true'

# MinIO client initialization
minio_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=boto3.session.Config(signature_version='s3v4'),
    use_ssl=MINIO_SECURE
)

# Helper function to upload file to MinIO and return metadata
async def upload_file_to_minio(
    file: UploadFile,
    bucket_name: str,
    object_prefix: str = "binaries" # e.g., "robot_firmware", "camera_config"
):
    try:
        # Read the file content
        file_content = await file.read()
        file_size = len(file_content)

        # Calculate checksum (e.g., SHA256)
        checksum = hashlib.sha256(file_content).hexdigest()

        # Define the object key (path in MinIO)
        # Using a UUID or timestamp could prevent name collisions if original_filename isn't unique
        # For simplicity, we'll use a prefix + original filename for now.
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        object_key = f"{object_prefix}/{timestamp_str}_{file.filename}"

        # Upload to MinIO
        minio_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=io.BytesIO(file_content), # Convert bytes to a BytesIO object for streaming
            ContentType=file.content_type if file.content_type else 'application/octet-stream',
            ContentLength=file_size,
            Metadata={ # Optional: Add custom metadata
                'checksum-sha256': checksum,
                'original-filename': file.filename
            }
        )
        logger.info(f"File '{file.filename}' uploaded to MinIO bucket '{bucket_name}' as '{object_key}'")

        return {
            "minio_object_key": object_key,
            "checksum": checksum,
            "file_size_bytes": file_size,
            "original_filename": file.filename
        }
    except ClientError as e:
        logger.error(f"MinIO ClientError during upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MinIO error during upload: {e}")
    except Exception as e:
        logger.error(f"Error during file upload to MinIO: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File upload failed: {e}")

# IMPORTANT: MinIO bucket name (create this manually or add creation logic)
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "recipe-binaries")

# Add a startup check to ensure the MinIO bucket exists
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event: Attempting to connect to DB and create tables...")
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")

        # Check MinIO connection and ensure bucket exists
        minio_client.list_buckets() # This line already exists
        logger.info("MinIO connection established during startup.")

        # Ensure the MinIO bucket exists
        if not minio_client.bucket_exists(Bucket=MINIO_BUCKET_NAME):
             minio_client.make_bucket(Bucket=MINIO_BUCKET_NAME)
             logger.info(f"MinIO bucket '{MINIO_BUCKET_NAME}' created.")
        else:
            logger.info(f"MinIO bucket '{MINIO_BUCKET_NAME}' already exists.")

    except Exception as e:
        logger.error(f"Failed to connect to database or MinIO or create bucket on startup: {e}")
        # Depending on criticality, you might want to exit here in production
        # sys.exit(1)

# --- Health Check Endpoint ---
@app.get("/")
async def root():
    return {"message": "Recipe Repository Service is running!"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    status = {"database": "unreachable", "minio": "unreachable"}

    # Check Database connection
    try:
        with db.connection() as connection:
            connection.execute(text("SELECT 1"))
        status["database"] = "reachable"
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Do not raise HTTPException immediately, check other services first

    # Check MinIO connection
    try:
        # Attempt to list buckets (a low-impact operation to check connectivity/auth)
        minio_client.list_buckets()
        status["minio"] = "reachable"
        logger.info("MinIO connection successful.")
    except ClientError as e:
        logger.error(f"MinIO connection failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"MinIO connection failed: {e}")

    if status["database"] == "reachable" and status["minio"] == "reachable":
        return {"status": "ok", "services": status}
    else:
        raise HTTPException(status_code=500, detail={"status": "degraded", "services": status})

# --- Software Component API Endpoints ---

@app.post("/recipes/{recipe_id}/components/upload", response_model=schemas.SoftwareComponentRead, status_code=status.HTTP_201_CREATED)
async def upload_software_component(
    recipe_id: int,
    component_type: str = Form(..., description="Type of the component (e.g., 'robot_firmware', 'camera_config')."),
    file: UploadFile = File(..., description="The binary file to upload."),
    db: Session = Depends(get_db)
):
    """
    Upload a binary software component and link it to a specific recipe.
    """
    db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")

    logger.info(f"Received upload for recipe_id={recipe_id}, filename={file.filename}, type={component_type}")

    # Upload file to MinIO and get its metadata
    uploaded_file_info = await upload_file_to_minio(
        file=file,
        bucket_name=MINIO_BUCKET_NAME,
        object_prefix=component_type # Use component_type as a folder prefix in MinIO
    )

    # Create the SoftwareComponent record in PostgreSQL
    db_software_component = models.SoftwareComponent(
        recipe_id=recipe_id,
        component_type=component_type,
        minio_object_key=uploaded_file_info["minio_object_key"],
        checksum=uploaded_file_info["checksum"],
        original_filename=uploaded_file_info["original_filename"],
        file_size_bytes=uploaded_file_info["file_size_bytes"]
    )
    db.add(db_software_component)
    db.commit()
    db.refresh(db_software_component)

    logger.info(f"Software component {db_software_component.id} ({db_software_component.original_filename}) linked to recipe {recipe_id}.")

    return db_software_component