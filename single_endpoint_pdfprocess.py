from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
from uuid import uuid4

app = FastAPI()

@app.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    # 1️⃣ Save uploaded file temporarily
    temp_input = f"temp_{uuid4()}_{file.filename}"
    with open(temp_input, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2️⃣ Process the file (your logic here)
    # Example: create output file
    temp_output = f"output_{uuid4()}_{file.filename}"
    with open(temp_output, "wb") as f:
        f.write(b"Processed file content\n")  # your real processing here

    # 3️⃣ Create a FileResponse and delete temp files after sending
    response = FileResponse(
        temp_output,
        filename=f"processed_{file.filename}",
        media_type=file.content_type
    )

    @response.call_on_close
    def cleanup():
        try:
            os.remove(temp_input)
            os.remove(temp_output)
        except:
            pass

    return response
