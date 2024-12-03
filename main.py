from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
import os
from typing import List, Optional
import fpdf
from datetime import datetime
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# PDF class
class PDF(fpdf.FPDF):
    def __init__(self, user, customer, invoice):
        super().__init__()
        self.invoice = invoice
        self.customer = customer
        self.user = user

    def header(self):
        # Issuer data in header (top-right corner)
        self.set_font("Arial", style="B", size=8)
        self.set_xy(120, 10)  # Position in the top-right corner
        self.cell(0, 5, "Podatki o izdajatelju:", 0, 1, "R")
        self.set_font("Arial", size=9)
        self.cell(0, 5, f"{self.user.name}", 0, 1, "R")
        self.cell(0, 5, f"{self.user.address.split(', ')[0]}", 0, 1, "R")
        self.cell(0, 5, f"{self.user.address.split(', ')[1]}", 0, 1, "R")
        self.cell(0, 5, f"Id. št. za DDV izdajatelja: SI{self.user.tax_number}", 0, 1, "R")
        self.cell(0, 5, f"Matična številka: {self.user.registration_number}", 0, 1, "R")
        self.cell(0, 5, f"T: {self.user.phone}", 0, 1, "R")
        if self.user.tax_payer:
            self.cell(0, 5, "Davčni zavezanec: DA", 0, 1, "R")
        self.ln(2)
        self.set_font("Arial", style="B", size=10)
        self.cell(0, 5, f"Obvezno plačilo na račun odprt pri {self.user.bank}", 0, 1, "R")
        self.cell(0, 5, f"IBAN: {self.user.iban}", 0, 1, "R")
        self.ln(2)

        self.set_xy(120, 70)  # Position in the top-right corner
        # Invoice number and issue date (below issuer data)
        self.set_font("Arial", style="B", size=10)
        self.cell(0, 5, f"RAČUN št.: {self.invoice.invoice_number}", 0, 1, "R")
        self.set_font("Arial", size=9)
        self.cell(0, 5, f"Datum izdaje: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, "R")
        self.ln(2)

        # Service dates (below invoice info)
        issue_date_formatted = (
            datetime.fromisoformat(self.invoice.issue_date[:-1]).strftime('%d.%m.%Y')
            if self.invoice.issue_date else 'Ni določeno'
        )
        due_date_formatted = (
            datetime.fromisoformat(self.invoice.due_date[:-1]).strftime('%d.%m.%Y')
            if self.invoice.due_date else 'Ni določeno'
        )
        self.cell(0, 5, f"Datum opravljene storitve: {issue_date_formatted}", 0, 1, "R")
        self.cell(0, 5, f"Datum zapadlosti računa: {due_date_formatted}", 0, 1, "R")
        self.ln(5)

# Function to generate the PDF
def generate_invoice(user, customer, invoice, services):
    # Create the PDF instance
    pdf = PDF(user=user, customer=customer, invoice=invoice)
    pdf.add_font("Arial", style="", fname="arial-unicode-ms.ttf", uni=True)
    pdf.add_font("Arial", style="B", fname="arial-unicode-ms-bold.ttf", uni=True)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Set a smaller font and tighter line spacing
    font_size = 9
    pdf.set_font("Arial", size=font_size)
    line_height = 5

    # Receiver Data (Top-Left Corner)
    pdf.set_xy(10, 60)
    pdf.set_font("Arial", style="B", size=8)
    pdf.cell(0, line_height, "Podatki o kupcu:", 0, 1)
    pdf.set_font("Arial", size=font_size, style="B")
    pdf.cell(0, line_height, f"{customer.name}", 0, 1)
    pdf.set_font("Arial", size=font_size)
    pdf.cell(0, line_height, f"{customer.address}", 0, 1)
    pdf.set_xy(10, 90)
    pdf.cell(0, line_height, f"Davčna številka: SI{customer.tax_number}", 0, 1)

    # Service Details
    pdf.set_font("Arial", style="B", size=font_size)
    pdf.set_font("Arial", size=font_size)
    pdf.set_xy(10, 110)

    # Table headers
    pdf.cell(50, line_height, "Naziv storitve", border=0)  # Left-aligned
    pdf.cell(15, line_height, "Količina", border=0, align="R")  # Right-aligned
    pdf.cell(15, line_height, "Enota", border=0, align="R")  # Right-aligned
    pdf.cell(20, line_height, "Cena (€)", border=0, align="R")  # Right-aligned
    pdf.cell(15, line_height, "Rab. %", border=0, align="R")  # Right-aligned
    pdf.cell(25, line_height, "Davčna osnova", border=0, align="R")  # Right-aligned
    pdf.cell(15, line_height, "DDV %", border=0, align="R")  # Right-aligned
    pdf.set_x(175)  # Set x position close to the right margin
    pdf.cell(25, line_height, "Skupaj (€)", border=0, align="R")  # Right-aligned
    pdf.ln(line_height)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())

    # Table rows
    total_sum = 0
    for service in services:
        quantity = 1
        price_sum = quantity * service.price
        rabat = service.rabat or 0  # Default Rabat % is 0 if not provided
        tax_base = price_sum * (1 - rabat / 100)
        tax_rate = 22  # Fixed DDV rate
        ddv = tax_base * (tax_rate / 100)
        sum_with_tax = tax_base + ddv
        total_sum += tax_base

        # Populate table rows
        pdf.cell(50, line_height, service.name, border=0)  # Left-aligned
        pdf.cell(15, line_height, f"{quantity}", border=0, align="R")  # Right-aligned
        pdf.cell(15, line_height, "kos", border=0, align="R")  # Right-aligned, always "kos"
        pdf.cell(20, line_height, f"{service.price:.2f}", border=0, align="R")  # Right-aligned
        pdf.cell(15, line_height, f"{rabat:.2f}", border=0, align="R")  # Right-aligned
        pdf.cell(25, line_height, f"{tax_base:.2f}", border=0, align="R")  # Right-aligned
        pdf.cell(15, line_height, f"{tax_rate}", border=0, align="R")  # Right-aligned

        # Skupaj (€): Manually align to the right edge
        pdf.set_x(175)  # Set x position close to the right margin
        pdf.cell(25, line_height, f"{sum_with_tax:.2f}", border=0, align="R")  # Right-aligned
        pdf.ln(line_height)

    # Tax Calculation
    tax = total_sum * 0.22
    sum_with_tax = total_sum + tax
    pdf.ln(line_height * 2)
    pdf.cell(0, line_height, f"Skupaj brez DDV: {total_sum:.2f} €", 0, 1, "R")
    pdf.cell(0, line_height, f"DDV (22%): {tax:.2f} €", 0, 1, "R")
    pdf.ln(line_height)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, line_height, f"Skupaj z DDV za plačilo: {sum_with_tax:.2f} €", 0, 1, "R")

    pdf.ln(line_height * 2)

    # Tax Recapitulation
    pdf.set_font("Arial", style="B", size=font_size)
    pdf.cell(0, line_height, "Rekapitulacija DDV:", 0, 1, "R")
    pdf.set_font("Arial", size=font_size)
    pdf.cell(0, line_height, f"{'DDV osnova':<18}{'DDV%':<10}{'Znesek DDV':<15}{'Skupaj':<0}", 0, 1, "R")
    pdf.cell(0, line_height, f"{total_sum:<20.2f}{22:<20}{tax:<10.2f}{sum_with_tax:<0.2f}", 0, 1, "R")
    pdf.ln(line_height * 2)

    # Signature
    pdf.set_y(250)  # Set x position close to the right margin
    pdf.cell(0, line_height, "Poslujemo brez žiga", 0, 1, "R")
    pdf.cell(0, line_height, "Franc Potočnik (Podpis)", 0, 1, "R")

    return pdf





# Initialize FastAPI
app = FastAPI()

# Pydantic Models
class Service(BaseModel):
    name: str
    price: float
    rabat: Optional[float] = 0

class User(BaseModel):
    name: str
    address: str
    tax_number: str
    registration_number: str
    phone: str
    tax_payer: bool
    bank: str
    iban: str

class Customer(BaseModel):
    name: str
    address: str
    tax_number: str

class Invoice(BaseModel):
    invoice_number: str
    issue_date: Optional[str] = None
    due_date: Optional[str] = None

class InvoiceRequest(BaseModel):
    user: User
    customer: Customer
    invoice: Invoice
    services: List[Service]



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.post("/generate-invoice/")
async def generate_invoice_api(invoice_request: InvoiceRequest):
    print("Received Data:", invoice_request)
    pdf = generate_invoice(
        user=invoice_request.user,
        customer=invoice_request.customer,
        invoice=invoice_request.invoice,
        services=invoice_request.services,
    )
    os.makedirs("./invoices", exist_ok=True)
    invoice_name = f"Invoice_{invoice_request.invoice.invoice_number}_{invoice_request.customer.name.replace('.', '').replace(',', '-').replace(' ', '-').replace('--', '-').lower()}.pdf"
    pdf_path = f"./invoices/{invoice_name}"
    pdf.output(pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=invoice_name)
