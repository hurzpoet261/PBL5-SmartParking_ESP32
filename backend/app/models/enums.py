import enum


class LotStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VehicleType(str, enum.Enum):
    MOTORBIKE = "motorbike"
    CAR = "car"
    BICYCLE = "bicycle"
    TRUCK = "truck"
    OTHER = "other"


class GateType(str, enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"
    BOTH = "both"


class GateStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class StaffRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerType(str, enum.Enum):
    WALK_IN = "walk_in"
    MONTHLY = "monthly"


class CardType(str, enum.Enum):
    GUEST = "guest"
    MONTHLY = "monthly"
    STAFF = "staff"


class CardStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    LOST = "lost"
    BLOCKED = "blocked"
    INACTIVE = "inactive"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    COVERED = "covered"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOST_CARD = "lost_card"
    ABNORMAL = "abnormal"


class PaymentType(str, enum.Enum):
    SINGLE = "single"
    MONTHLY = "monthly"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    E_WALLET = "e_wallet"


class PaymentRecordStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class DeviceType(str, enum.Enum):
    RFID_READER = "rfid_reader"
    CAMERA = "camera"
    BARRIER = "barrier"
    GAS_SENSOR = "gas_sensor"
    ESP32_CONTROLLER = "esp32_controller"
    DISPLAY = "display"
    OTHER = "other"


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class AlertType(str, enum.Enum):
    GAS = "gas"
    DEVICE_OFFLINE = "device_offline"
    PLATE_MISMATCH = "plate_mismatch"
    BARRIER_ERROR = "barrier_error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    OTHER = "other"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
