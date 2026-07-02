from pydantic import BaseModel
from typing import Optional

PERMISSION_KEYS: list[str] = [
    "create_booking",
    "view_own_bookings",
    "view_all_bookings",
    "cancel_booking",
    "edit_booking_status",
    "generate_report",
    "view_reports",
    "download_reports",
    "delete_reports",
    "manage_patients",
    "view_patient_history",
    "manage_tests",
    "view_dashboard",
    "view_reports_today",
    "manage_users",
    "manage_roles",
    "update_collection_address",
    "view_collection_address",
]


class PatientCreate(BaseModel):
    name: str
    phone: str
    address: str = ""


class PatientResponse(BaseModel):
    patient_id: str
    name: str
    phone: str
    address: str
    created_at: str


class BookingCreate(BaseModel):
    patient_name: str
    patient_phone: str
    test_name: str
    collection_address: str


class BookingResponse(BaseModel):
    booking_id: str
    patient_id: str
    patient_name: str
    patient_phone: str
    test_name: str
    collection_address: str
    status: str
    created_at: str


class DoctorResponse(BaseModel):
    doctor_id: str
    name: str
    speciality: str
    qualifications: str
    bio: str


class TestResponse(BaseModel):
    test_id: str
    name: str
    price: float
    description: str
    category: str


class ReportCreate(BaseModel):
    booking_id: str
    results: str


class ReportResponse(BaseModel):
    report_id: str
    booking_id: str
    patient_id: str
    test_name: str
    results: str
    parameter_values: str = ""
    pdf_path: str = ""
    generated_at: str


class BookingStatusUpdate(BaseModel):
    status: str


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    token: str
    username: str
    role: str


class AdminPatientResponse(BaseModel):
    patient_id: str
    name: str
    phone: str
    address: str
    created_at: str


class AdminBookingResponse(BaseModel):
    booking_id: str
    patient_id: str
    patient_name: str
    patient_phone: str
    test_name: str
    collection_address: str
    status: str
    created_at: str


class AdminReportResponse(BaseModel):
    report_id: str
    booking_id: str
    patient_id: str
    test_name: str
    results: str
    generated_at: str


class AdminDashboardResponse(BaseModel):
    total_patients: int
    total_bookings: int
    todays_bookings: int
    reports_today: int


class DoctorUpdate(BaseModel):
    name: str
    speciality: str
    qualifications: str
    bio: str


class TestUpdate(BaseModel):
    name: str
    price: float
    description: str
    category: str


class AdminReportCreate(BaseModel):
    booking_id: str
    results: str


class AdminBookingStatusUpdate(BaseModel):
    status: str


class ParameterResponse(BaseModel):
    name: str
    unit: str
    normal_range: str


class GeneratePdfRequest(BaseModel):
    parameter_values: dict[str, str]


class PdfGeneratedResponse(BaseModel):
    report_id: str
    booking_id: str
    test_name: str
    pdf_path: str
    generated_at: str


class PermissionToggle(BaseModel):
    role: str
    permission_key: str
    enabled: bool


class BulkPermissionsRequest(BaseModel):
    permissions: list[PermissionToggle]


class PermissionsResponse(BaseModel):
    permissions: dict[str, dict[str, bool]]
