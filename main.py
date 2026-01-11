from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid
from pdf_image_extract import remove_large_image_xobjects
from pathlib import Path
import glob
from datetime import datetime, timedelta


#app = FastAPI()
app = FastAPI(redirect_slashes=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("./static", exist_ok=True)
app.mount("/.static", StaticFiles(directory=".static"), name=".static")
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(".static", exist_ok=True)

def cleanup_old_files(directory, days_old=7):
    """Remove files older than specified days"""
    try:
        cutoff_time = datetime.now() - timedelta(days=days_old)
        for file_path in glob.glob(os.path.join(directory, "*")):
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    print(f"Cleaned up old file: {file_path}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

@app.get("/")
def read_root():
    return {"message": "FastAPI is running!", "version": "1.0.0"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (check content length if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / (1024*1024)}MB limit")
    
    uid = uuid.uuid4().hex[:10]
    # Sanitize filename to prevent path traversal
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")
    file_location = os.path.join(UPLOAD_DIR, f"{uid}_{safe_filename}")
    
    try:
        file_size = 0
        with open(file_location, "wb") as buffer:
            # Streaming copy with size check
            while True:
                chunk = await file.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_location)
                    raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / (1024*1024)}MB limit")
                buffer.write(chunk)
        
        # Verify file is a valid PDF by checking magic bytes
        with open(file_location, "rb") as f:
            header = f.read(4)
            if header != b'%PDF':
                os.remove(file_location)
                raise HTTPException(status_code=400, detail="Invalid PDF file format")
        
        # Cleanup old files periodically
        cleanup_old_files(UPLOAD_DIR, days_old=7)
        cleanup_old_files(".static", days_old=7)
        
        return JSONResponse({
            "status": "success",
            "message": "Upload Successful",
            "file_location": file_location,
            "file_size": file_size
        })
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"File saving error: {str(e)}")

@app.post("/process/{filename:path}")
async def process_pdf(filename: str):
    try:
        # Security: Ensure filename is within allowed directory
        if not filename.startswith(UPLOAD_DIR):
            raise HTTPException(status_code=403, detail="Invalid file path")
        
        # Validate that the file exists
        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Verify it's actually a PDF file
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File is not a PDF")
        
        # Verify it's a valid PDF by checking magic bytes
        try:
            with open(filename, "rb") as f:
                header = f.read(4)
                if header != b'%PDF':
                    raise HTTPException(status_code=400, detail="Invalid PDF file format")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot read file: {str(e)}")
        
        # Generate unique output filename
        uid2 = uuid.uuid4().hex[:7]
        timestamp = datetime.now().strftime("%Y%m%d")
        process_pdf_path = os.path.join(".static", f"{uid2}_{timestamp}_Process.pdf")
        
        # Ensure .static directory exists
        os.makedirs(".static", exist_ok=True)
        
        # Process the PDF with proper error handling
        try:
            remove_large_image_xobjects(filename, process_pdf_path)
        except Exception as process_error:
            # Clean up if processing failed
            if os.path.exists(process_pdf_path):
                os.remove(process_pdf_path)
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(process_error)}")
        
        # Verify the processed file was created and is valid
        if not os.path.exists(process_pdf_path):
            raise HTTPException(status_code=500, detail="Processing failed - output file not created")
        
        # Verify output file is a valid PDF
        try:
            with open(process_pdf_path, "rb") as f:
                header = f.read(4)
                if header != b'%PDF':
                    os.remove(process_pdf_path)
                    raise HTTPException(status_code=500, detail="Processing failed - invalid output file")
        except Exception:
            if os.path.exists(process_pdf_path):
                os.remove(process_pdf_path)
            raise HTTPException(status_code=500, detail="Processing failed - cannot verify output file")
        
        # Get file size for response
        file_size = os.path.getsize(process_pdf_path)
        
        # Return the URL path for accessing the file (relative to static mount)
        process_filename = os.path.basename(process_pdf_path)
        process_url = f"/.static/{process_filename}"
        
        print(f"Successfully processed {filename} -> {process_pdf_path}")
        return JSONResponse({
            "processing": "false",
            "processfile": process_url,
            "process_filename": process_filename,
            "size": file_size,
            "processed_path": process_pdf_path
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
 
@app.get("/download/{filename}")
async def download_file(filename: str):
    try:
        # Security: Only allow files from .static directory
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files can be downloaded")
        
        file_path = os.path.join(".static", filename)
        
        # Prevent directory traversal
        if not os.path.abspath(file_path).startswith(os.path.abspath(".static")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
