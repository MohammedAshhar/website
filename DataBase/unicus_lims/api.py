import hashlib
import json
import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .database import Database
from .schemas import (
    PatientCreate, PatientResponse,
    BookingCreate, BookingResponse,
    BookingStatusUpdate,
    DoctorResponse, TestResponse,
    ReportCreate, ReportResponse,
    AdminLogin, AdminTokenResponse,
    AdminDashboardResponse,
    DoctorUpdate, TestUpdate,
    AdminBookingStatusUpdate, AdminReportCreate,
    ParameterResponse, GeneratePdfRequest, PdfGeneratedResponse,
    PermissionToggle, BulkPermissionsRequest, PermissionsResponse,
    PERMISSION_KEYS,
)
from .test_params import PARAM_MAP
from .pdf_generator import generate_report_pdf, REPORTS_DIR
from . import sheets_sync


ROOT_DIR = Path(__file__).resolve().parent.parent.parent

ADMIN_TOKENS: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _static_file_response(path: str):
    full = ROOT_DIR / path
    if full.exists() and full.is_file():
        return FileResponse(str(full))
    full = ROOT_DIR / "index.html"
    if full.exists():
        return FileResponse(str(full))
    raise HTTPException(404, "Not found")


def create_fastapi_app(database: Database) -> FastAPI:
    app = FastAPI(title="Unicus Diagnostics", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.database = database

    # --- Auth helpers ---

    def require_admin(authorization: str | None = Header(None)):
        if not authorization:
            raise HTTPException(401, "Unauthorized")
        token = authorization.replace("Bearer ", "")
        if token not in ADMIN_TOKENS:
            raise HTTPException(401, "Invalid token")
        return ADMIN_TOKENS[token]

    def require_owner(current_admin: dict = Depends(require_admin)):
        if current_admin.get("role") != "owner":
            raise HTTPException(403, "Only the owner can perform this action")
        return current_admin

    def require_permission(perm_key: str):
        """
        Factory that returns a FastAPI dependency to check whether the
        authenticated user's role has the given permission enabled.
        Owner always passes (bypasses permission checks entirely).
        Usage in endpoint: _=Depends(require_permission("create_booking"))
        """
        def _checker(current_admin: dict = Depends(require_admin)):
            role = current_admin.get("role", "")
            if role == "owner":
                return current_admin
            perms = database.get_role_permissions(role)
            if not perms.get(perm_key, False):
                raise HTTPException(403, f"Permission denied: '{perm_key}' required")
            return current_admin
        return _checker

    # --- Auth endpoints ---

    @app.post("/api/admin/login")
    def admin_login(body: AdminLogin):
        user = database.get_admin_user(body.username)
        if not user:
            raise HTTPException(401, "Invalid credentials")
        if user["password_hash"] != _hash_password(body.password):
            raise HTTPException(401, "Invalid credentials")
        token = str(uuid.uuid4())
        ADMIN_TOKENS[token] = {"username": body.username, "role": user["role"]}
        return AdminTokenResponse(token=token, username=body.username, role=user["role"])

    @app.post("/api/admin/logout")
    def admin_logout(authorization: str | None = Header(None)):
        if authorization:
            token = authorization.replace("Bearer ", "")
            ADMIN_TOKENS.pop(token, None)
        return {"status": "ok"}

    # --- Admin dashboard ---

    @app.get("/api/admin/dashboard")
    def admin_dashboard(_=Depends(require_permission("view_dashboard"))):
        return AdminDashboardResponse(
            total_patients=database.get_all_patients_count(),
            total_bookings=database.get_all_bookings_count(),
            todays_bookings=database.get_todays_bookings_count(),
            reports_today=database.get_reports_today_count(),
        )

    # --- Admin patient list ---

    @app.get("/api/admin/patients")
    def admin_list_patients(_=Depends(require_permission("manage_patients"))):
        return database.list_all_patients()

    # --- Admin booking list & update ---

    @app.get("/api/admin/bookings")
    def admin_list_bookings(status: str = None, _=Depends(require_permission("view_all_bookings"))):
        bookings = database.list_all_bookings()
        if status:
            bookings = [b for b in bookings if b["status"] == status]
        return bookings

    @app.put("/api/admin/booking/{booking_id}/status")
    def admin_update_booking_status(booking_id: str, body: AdminBookingStatusUpdate, _=Depends(require_permission("edit_booking_status"))):
        try:
            database.update_booking_status(booking_id, body.status)
        except ValueError as e:
            raise HTTPException(404, str(e))
        except RuntimeError as e:
            raise HTTPException(500, str(e))
        return {"status": "ok"}

    # --- Admin reports ---

    @app.get("/api/admin/reports")
    def admin_list_reports(_=Depends(require_permission("view_reports"))):
        return database.list_all_reports()

    @app.post("/api/admin/report/create")
    def admin_create_report(body: AdminReportCreate, _=Depends(require_permission("generate_report"))):
        try:
            uuid.UUID(body.booking_id)
        except ValueError:
            raise HTTPException(400, "Invalid booking ID format")
        booking = database.get_booking(body.booking_id)
        if not booking:
            raise HTTPException(404, "Booking not found")
        report = database.create_report(
            body.booking_id,
            str(booking.patient_id),
            booking.test_name,
            body.results,
        )
        return {
            "report_id": str(report.report_id),
            "booking_id": str(report.booking_id),
            "test_name": report.test_name,
            "results": report.results,
            "generated_at": report.generated_at,
        }

    @app.put("/api/admin/report/{report_id}")
    def admin_update_report(report_id: str, body: ReportCreate, _=Depends(require_permission("generate_report"))):
        database.update_report(report_id, body.results)
        return {"status": "ok"}

    # --- PDF Report Generation ---

    @app.get("/api/admin/tests/{test_name}/parameters")
    def admin_get_test_parameters(test_name: str, _=Depends(require_admin)):
        """
        Return the parameter template for a given test name.
        The test_name is matched case-insensitively against PARAM_MAP keys.
        """
        for key, params in PARAM_MAP.items():
            if key.lower() == test_name.lower():
                return [ParameterResponse(name=p.name, unit=p.unit, normal_range=p.normal_range) for p in params]
        raise HTTPException(404, f"Unknown test: {test_name}")

    @app.post("/api/admin/bookings/{booking_id}/generate-pdf")
    def admin_generate_pdf(booking_id: str, body: GeneratePdfRequest, _=Depends(require_permission("generate_report"))):
        """
        Generate a PDF report for a booking using the submitted parameter values.
        1. Fetch the booking and associated report (or create one).
        2. Validate the test type and fetch its parameter definitions.
        3. Call generate_report_pdf() to create the PDF file.
        4. Persist the report data (parameter_values, pdf_path) to all tables.
        """
        booking = database.get_booking(booking_id)
        if not booking:
            raise HTTPException(404, "Booking not found")

        test_name = booking.test_name
        params = None
        for key, p_list in PARAM_MAP.items():
            if key.lower() == test_name.lower():
                params = p_list
                break
        if not params:
            raise HTTPException(400, f"No parameter definitions for test: {test_name}")

        # Build results text
        results_lines = []
        for p in params:
            val = body.parameter_values.get(p.name, "")
            results_lines.append(f"{p.name}: {val} {p.unit}")
        results_text = "\n".join(results_lines)
        parameter_values_json = json.dumps(body.parameter_values)

        # Generate PDF
        try:
            pdf_path = generate_report_pdf(
                booking_id=booking_id,
                patient_name=booking.patient_name,
                patient_phone=booking.patient_phone,
                patient_address="",
                test_name=test_name,
                parameter_values=body.parameter_values,
                parameters=params,
                collection_address=booking.collection_address,
            )
        except Exception as exc:
            raise HTTPException(500, f"PDF generation failed: {exc}")

        from datetime import datetime
        now = datetime.utcnow()
        bid = uuid.UUID(booking_id)
        pid = uuid.UUID(str(booking.patient_id))

        existing = database.get_report_by_booking(booking_id)
        if existing:
            rid = uuid.UUID(str(existing.report_id))
            database.update_report(str(rid), results_text)
            database.update_report_pdf(str(rid), pdf_path)
        else:
            rid = uuid.uuid4()
            database.session.execute(
                database.prepared.report_insert,
                [rid, bid, pid, test_name, results_text, parameter_values_json, pdf_path, now],
            )

        database.session.execute(
            "INSERT INTO reports_by_booking (booking_id, report_id, patient_id, test_name, results, parameter_values, pdf_path, generated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [bid, rid, pid, test_name, results_text, parameter_values_json, pdf_path, now],
        )
        database.session.execute(
            "INSERT INTO all_reports (partition, generated_at, report_id, booking_id, patient_id, test_name, results, parameter_values, pdf_path) VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s)",
            [now, rid, bid, pid, test_name, results_text, parameter_values_json, pdf_path],
        )

        return PdfGeneratedResponse(
            report_id=str(rid),
            booking_id=booking_id,
            test_name=test_name,
            pdf_path=pdf_path,
            generated_at=str(now),
        )

    @app.get("/api/admin/reports/{booking_id}/download")
    def admin_download_pdf(booking_id: str, _=Depends(require_admin)):
        """
        Serve the generated PDF file for a given booking.
        First checks the database for the stored file path,
        then falls back to looking in the generated_reports/ directory.
        """
        pdf_candidate = REPORTS_DIR / f"{booking_id}.pdf"
        if pdf_candidate.exists():
            return FileResponse(str(pdf_candidate), media_type="application/pdf",
                                filename=f"report_{booking_id}.pdf")
        # Fall back to the path stored in the database
        report = database.get_report_by_booking(booking_id)
        if report and report.pdf_path:
            pdf_path = report.pdf_path
            if os.path.exists(pdf_path):
                return FileResponse(pdf_path, media_type="application/pdf",
                                    filename=f"report_{booking_id}.pdf")
        raise HTTPException(404, "PDF not found for this booking")

    # --- Admin doctors ---

    @app.put("/api/admin/doctor/{doctor_id}")
    def admin_update_doctor(doctor_id: str, body: DoctorUpdate, _=Depends(require_admin)):
        database.update_doctor(doctor_id, body.name, body.speciality, body.qualifications, body.bio)
        return {"status": "ok"}

    # --- Admin tests ---

    @app.put("/api/admin/test/{test_id}")
    def admin_update_test(test_id: str, body: TestUpdate, _=Depends(require_permission("manage_tests"))):
        database.update_test(test_id, body.name, body.price, body.description, body.category)
        return {"status": "ok"}

    @app.post("/api/admin/sync-prices")
    def admin_sync_prices(_=Depends(require_permission("manage_tests"))):
        """
        Sync test catalog from Google Sheets.
        1. Fetch products from the registered Google Sheet via gspread.
        2. Delete all existing tests from the database.
        3. Upsert each product from the sheet.
        4. Return the updated test list.
        """
        try:
            products = sheets_sync.fetch_products()
        except Exception as exc:
            raise HTTPException(502, f"Failed to read Google Sheet: {exc}")
        database.delete_all_tests()
        for p in products:
            database.upsert_test_by_name(p["name"], p["price"], p["description"], p["category"])
        tests = database.list_tests()
        return [
            TestResponse(
                test_id=str(t.test_id),
                name=t.name,
                price=t.price,
                description=t.description,
                category=t.category,
            )
            for t in tests
        ]

    # --- Permissions (owner only) ---

    @app.get("/api/admin/permissions", response_model=PermissionsResponse)
    def admin_get_permissions(_=Depends(require_owner)):
        """
        Returns all permission toggles grouped by role.
        Owner-only endpoint. Returns all stored permissions for admin and desk roles.
        """
        perms = database.get_all_permissions()
        return PermissionsResponse(permissions=perms)

    @app.put("/api/admin/permissions", response_model=PermissionsResponse)
    def admin_set_permissions(body: BulkPermissionsRequest, _=Depends(require_owner)):
        """
        Bulk upsert permissions for one or more roles.
        Owner-only endpoint. Accepts a list of PermissionToggle objects.
        Each toggle specifies role, permission_key, and enabled (boolean).
        """
        for toggle in body.permissions:
            database.set_role_permission(toggle.role, toggle.permission_key, toggle.enabled)
        perms = database.get_all_permissions()
        return PermissionsResponse(permissions=perms)

    # --- Patient endpoints ---

    @app.post("/api/patient/create", response_model=PatientResponse)
    def create_patient(body: PatientCreate):
        existing = database.get_patient_by_phone(body.phone)
        if existing:
            return PatientResponse(
                patient_id=str(existing.patient_id),
                name=existing.name,
                phone=existing.phone,
                address=existing.address,
                created_at=existing.created_at,
            )
        patient = database.create_patient(body.name, body.phone, body.address)
        return PatientResponse(
            patient_id=str(patient.patient_id),
            name=patient.name,
            phone=patient.phone,
            address=patient.address,
            created_at=patient.created_at,
        )

    @app.get("/api/patient/phone/{phone}", response_model=PatientResponse)
    def get_patient_by_phone(phone: str):
        patient = database.get_patient_by_phone(phone)
        if not patient:
            raise HTTPException(404, "Patient not found")
        return PatientResponse(
            patient_id=str(patient.patient_id),
            name=patient.name,
            phone=patient.phone,
            address=patient.address,
            created_at=patient.created_at,
        )

    @app.get("/api/patient/{patient_id}", response_model=PatientResponse)
    def get_patient(patient_id: str):
        patient = database.get_patient(patient_id)
        if not patient:
            raise HTTPException(404, "Patient not found")
        return PatientResponse(
            patient_id=str(patient.patient_id),
            name=patient.name,
            phone=patient.phone,
            address=patient.address,
            created_at=patient.created_at,
        )

    # --- Booking endpoints ---

    @app.post("/api/booking/create", response_model=BookingResponse)
    def create_booking(body: BookingCreate):
        patient = database.get_patient_by_phone(body.patient_phone)
        if not patient:
            patient = database.create_patient(body.patient_name, body.patient_phone, body.collection_address)
        booking = database.create_booking(
            str(patient.patient_id),
            body.patient_name,
            body.patient_phone,
            body.test_name,
            body.collection_address,
        )
        return BookingResponse(
            booking_id=str(booking.booking_id),
            patient_id=str(booking.patient_id),
            patient_name=booking.patient_name,
            patient_phone=booking.patient_phone,
            test_name=booking.test_name,
            collection_address=booking.collection_address,
            status=booking.status,
            created_at=booking.created_at,
        )

    @app.get("/api/booking/{booking_id}", response_model=BookingResponse)
    def get_booking(booking_id: str):
        booking = database.get_booking(booking_id)
        if not booking:
            raise HTTPException(404, "Booking not found")
        return BookingResponse(
            booking_id=str(booking.booking_id),
            patient_id=str(booking.patient_id),
            patient_name=booking.patient_name,
            patient_phone=booking.patient_phone,
            test_name=booking.test_name,
            collection_address=booking.collection_address,
            status=booking.status,
            created_at=booking.created_at,
        )

    @app.get("/api/bookings/{phone}")
    def list_bookings(phone: str):
        bookings = database.list_bookings_by_phone(phone)
        return [
            BookingResponse(
                booking_id=str(b.booking_id),
                patient_id=str(b.patient_id),
                patient_name=b.patient_name,
                patient_phone=b.patient_phone,
                test_name=b.test_name,
                collection_address=b.collection_address,
                status=b.status,
                created_at=b.created_at,
            )
            for b in bookings
        ]

    # --- Doctor endpoints ---

    @app.get("/api/doctors", response_model=list[DoctorResponse])
    def list_doctors():
        doctors = database.list_doctors()
        return [
            DoctorResponse(
                doctor_id=str(d.doctor_id),
                name=d.name,
                speciality=d.speciality,
                qualifications=d.qualifications,
                bio=d.bio,
            )
            for d in doctors
        ]

    # --- Test endpoints ---

    @app.get("/api/tests", response_model=list[TestResponse])
    def list_tests():
        tests = database.list_tests()
        return [
            TestResponse(
                test_id=str(t.test_id),
                name=t.name,
                price=t.price,
                description=t.description,
                category=t.category,
            )
            for t in tests
        ]

    # --- Report endpoints ---

    @app.post("/api/report/create", response_model=ReportResponse)
    def create_report(body: ReportCreate):
        booking = database.get_booking(body.booking_id)
        if not booking:
            raise HTTPException(404, "Booking not found")
        report = database.create_report(
            body.booking_id,
            str(booking.patient_id),
            booking.test_name,
            body.results,
        )
        return ReportResponse(
            report_id=str(report.report_id),
            booking_id=str(report.booking_id),
            patient_id=str(report.patient_id),
            test_name=report.test_name,
            results=report.results,
            generated_at=report.generated_at,
        )

    @app.get("/api/report/{booking_id}")
    def get_report(booking_id: str):
        report = database.get_report_by_booking(booking_id)
        if not report:
            raise HTTPException(404, "Report not found for this booking")
        return ReportResponse(
            report_id=str(report.report_id),
            booking_id=str(report.booking_id),
            patient_id=str(report.patient_id),
            test_name=report.test_name,
            results=report.results,
            parameter_values=report.parameter_values,
            pdf_path=report.pdf_path,
            generated_at=report.generated_at,
        )

    @app.get("/api/report/{booking_id}/download")
    def download_report_pdf(booking_id: str):
        """
        Public endpoint to download a generated PDF report for a booking.
        No admin auth required (same security level as viewing the report text).
        """
        report = database.get_report_by_booking(booking_id)
        if not report:
            raise HTTPException(404, "Report not found for this booking")
        pdf_candidate = REPORTS_DIR / f"{booking_id}.pdf"
        if pdf_candidate.exists():
            return FileResponse(str(pdf_candidate), media_type="application/pdf",
                                filename=f"report_{booking_id}.pdf")
        if report.pdf_path and os.path.exists(report.pdf_path):
            return FileResponse(report.pdf_path, media_type="application/pdf",
                                filename=f"report_{booking_id}.pdf")
        raise HTTPException(404, "PDF not generated yet for this report")

    # --- Seed ---

    @app.post("/api/seed")
    def seed_data():
        database.seed_doctors()
        database.seed_tests()
        return {"status": "ok", "message": "Doctors and tests seeded"}

    # --- Static file serving (catch-all, must be last) ---

    @app.get("/{path:path}")
    def serve_static(path: str):
        full = ROOT_DIR / path
        if full.exists() and full.is_file():
            return FileResponse(str(full))
        idx = ROOT_DIR / "index.html"
        if idx.exists():
            return FileResponse(str(idx))
        raise HTTPException(404, "Not found")

    return app
