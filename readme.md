How to Run:
Install required libraries:
bash
Copy code
pip install fastapi uvicorn pydantic fpdf
Run the FastAPI server:
bash
Copy code
uvicorn main:app --reload
Use a tool like Postman or cURL to send a POST request to /generate-invoice/ with the appropriate JSON body.