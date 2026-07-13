# 2. Backend Architecture (Clean Architecture)

## 2.1 Layer Dependency Rules

```
STRICT DEPENDENCY FLOW (inward only):

  Controllers ──▶ Services ──▶ Repositories ──▶ Models
       │              │
       ▼              ▼
     DTOs          Utilities
                      │
                      ▼
                    Config
```

**Rules:**
1. Controllers ONLY call Services (never Repositories directly)
2. Services ONLY call Repositories for data access
3. Repositories ONLY use SQLAlchemy Models and ChromaDB client
4. DTOs handle all serialization/deserialization
5. No circular dependencies between layers
6. Utilities are stateless helper functions

## 2.2 Controller Layer (Flask Blueprints)

Each controller is a Flask Blueprint responsible for:
- Route definition and HTTP method handling
- Request parsing (query params, body, path params)
- Input validation via Marshmallow schemas
- Calling appropriate service methods
- Formatting responses using the standard envelope
- Error handling via decorators

**Pattern:**
```python
# Example: TicketController (tickets/controller.py)

from flask import Blueprint, request
from app.services.ticket_service import TicketService
from app.dtos.ticket_dto import CreateTicketSchema, TicketResponseSchema
from app.utils.decorators import jwt_required, role_required, validate_input
from app.utils.response import success_response, created_response

ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/v1/tickets')

@ticket_bp.route('/', methods=['POST'])
@jwt_required
@validate_input(CreateTicketSchema)
def create_ticket(validated_data):
    """Create a new support ticket."""
    ticket = TicketService.create(validated_data, current_user)
    return created_response(TicketResponseSchema().dump(ticket))

@ticket_bp.route('/', methods=['GET'])
@jwt_required
def list_tickets():
    """List tickets with filtering, sorting, pagination."""
    filters = TicketService.parse_filters(request.args)
    result = TicketService.list(filters, current_user)
    return success_response(TicketResponseSchema(many=True).dump(result.items),
                           pagination=result.pagination)
```

## 2.3 Service Layer

Each service encapsulates business logic for one domain:
- Business rule validation
- Authorization enforcement
- Orchestration of multiple repositories
- External API calls (Groq, Cloudinary, Gmail)
- Event emission (for WebSocket/notifications)
- Audit log creation

**Pattern:**
```python
# Example: TicketService (services/ticket_service.py)

class TicketService:
    @staticmethod
    def create(data: dict, current_user: User) -> Ticket:
        """Create ticket with AI classification."""
        # 1. Generate ticket ID
        ticket_id = TicketService._generate_ticket_id()
        
        # 2. AI classification (async-safe)
        ai_result = AIService.classify_ticket(data['title'], data['description'])
        
        # 3. Apply AI suggestions if user didn't provide
        if not data.get('category'):
            data['category'] = ai_result.get('category')
        if not data.get('priority'):
            data['priority'] = ai_result.get('priority')
        if not data.get('department_id'):
            data['department_id'] = ai_result.get('department_id')
        
        # 4. Create ticket record
        ticket = TicketRepository.create({
            **data,
            'ticket_number': ticket_id,
            'requester_id': current_user.id,
            'status': TicketStatus.NEW,
            'ai_confidence': ai_result.get('confidence', 0)
        })
        
        # 5. Create audit log
        AuditService.log(action='ticket_created', resource=ticket, user=current_user)
        
        # 6. Send notifications
        NotificationService.notify_ticket_created(ticket)
        
        # 7. Emit WebSocket event
        socketio.emit('ticket_created', {'ticket_id': ticket.id}, room=f'dept_{ticket.department_id}')
        
        return ticket
```

## 2.4 Repository Layer

Each repository handles data access for one entity:
- CRUD operations via SQLAlchemy
- Complex query building with filters, joins, pagination
- No business logic (pure data access)
- Returns SQLAlchemy model instances

**Pattern:**
```python
# Example: TicketRepository (repositories/ticket_repository.py)

class TicketRepository:
    @staticmethod
    def create(data: dict) -> Ticket:
        ticket = Ticket(**data)
        db.session.add(ticket)
        db.session.commit()
        return ticket
    
    @staticmethod
    def get_by_id(ticket_id: int) -> Ticket | None:
        return Ticket.query.get(ticket_id)
    
    @staticmethod
    def list_with_filters(filters: dict, page: int, per_page: int) -> Pagination:
        query = Ticket.query
        
        if filters.get('status'):
            query = query.filter(Ticket.status == filters['status'])
        if filters.get('priority'):
            query = query.filter(Ticket.priority == filters['priority'])
        if filters.get('department_id'):
            query = query.filter(Ticket.department_id == filters['department_id'])
        if filters.get('assignee_id'):
            query = query.filter(Ticket.assignee_id == filters['assignee_id'])
        
        sort_field = getattr(Ticket, filters.get('sort_by', 'created_at'))
        order = sort_field.desc() if filters.get('order') == 'desc' else sort_field.asc()
        
        return query.order_by(order).paginate(page=page, per_page=per_page)
```

## 2.5 DTO Layer (Marshmallow Schemas)

Separate schemas for request validation and response serialization:

```python
# Example: TicketDTO (dtos/ticket_dto.py)

from marshmallow import Schema, fields, validate

class CreateTicketSchema(Schema):
    """Validates ticket creation input."""
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(required=True, validate=validate.Length(min=10, max=5000))
    category = fields.Str(validate=validate.OneOf([...]))  # Optional — AI fills if missing
    priority = fields.Str(validate=validate.OneOf(['critical', 'high', 'medium', 'low']))
    department_id = fields.Int()
    project_id = fields.Int()

class TicketResponseSchema(Schema):
    """Serializes ticket for API response."""
    id = fields.Int()
    ticket_number = fields.Str()
    title = fields.Str()
    description = fields.Str()
    status = fields.Str()
    priority = fields.Str()
    category = fields.Str()
    requester = fields.Nested(UserSummarySchema)
    assignee = fields.Nested(UserSummarySchema)
    department = fields.Nested(DepartmentSummarySchema)
    sla_deadline = fields.DateTime()
    ai_confidence = fields.Float()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
```

## 2.6 Model Layer (SQLAlchemy)

```python
# Example: Ticket Model (models/ticket.py)

class Ticket(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=TicketStatus.NEW, index=True)
    priority = db.Column(db.String(20), index=True)
    category = db.Column(db.String(50), index=True)
    
    # Foreign keys
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    # AI metadata
    ai_confidence = db.Column(db.Float, default=0.0)
    ai_category_suggestion = db.Column(db.String(50))
    ai_priority_suggestion = db.Column(db.String(20))
    
    # SLA
    sla_response_deadline = db.Column(db.DateTime)
    sla_resolution_deadline = db.Column(db.DateTime)
    first_responded_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], backref='requested_tickets')
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_tickets')
    department = db.relationship('Department', backref='tickets')
    project = db.relationship('Project', backref='tickets')
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic')
```

## 2.7 Utility Layer

| Utility | Purpose |
|---------|---------|
| `decorators.py` | `@jwt_required`, `@role_required(roles)`, `@validate_input(schema)`, `@rate_limit` |
| `response.py` | `success_response()`, `created_response()`, `error_response()`, `paginated_response()` |
| `exceptions.py` | Custom exception classes: `NotFoundError`, `ValidationError`, `AuthorizationError`, `AIServiceError` |
| `helpers.py` | Date formatting, ID generation, slug creation, file validation |
| `validators.py` | Email validation, password strength, file type checking |
| `constants.py` | Enums for TicketStatus, Priority, Category, UserRole |
| `logger.py` | Structured JSON logger with correlation ID |

## 2.8 Config Layer

```python
# config/settings.py

class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    CELERY_BROKER_URL = os.environ.get('REDIS_URL')
    CHROMA_PERSIST_DIR = os.environ.get('CHROMA_DIR', './chroma_data')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://...')

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## 2.9 Error Handling Strategy

```python
# Global error handler registration

@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return error_response(code='VALIDATION_ERROR', message=str(e), status=400)

@app.errorhandler(NotFoundError)
def handle_not_found(e):
    return error_response(code='NOT_FOUND', message=str(e), status=404)

@app.errorhandler(AuthorizationError)
def handle_forbidden(e):
    return error_response(code='FORBIDDEN', message=str(e), status=403)

@app.errorhandler(AIServiceError)
def handle_ai_error(e):
    return error_response(code='AI_SERVICE_ERROR', message='AI service temporarily unavailable', status=503)

@app.errorhandler(429)
def handle_rate_limit(e):
    return error_response(code='RATE_LIMIT_EXCEEDED', message='Too many requests', status=429)

@app.errorhandler(500)
def handle_internal_error(e):
    logger.exception('Internal server error')
    return error_response(code='INTERNAL_ERROR', message='An unexpected error occurred', status=500)
```

## 2.10 Extension Registration Pattern

```python
# extensions.py — all Flask extensions initialized once

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from celery import Celery

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
ma = Marshmallow()
cors = CORS()
socketio = SocketIO()
limiter = Limiter()
celery = Celery()
```

```python
# app/__init__.py — Application Factory

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    cors.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    limiter.init_app(app)
    
    # Register blueprints
    from app.controllers.auth_controller import auth_bp
    from app.controllers.ticket_controller import ticket_bp
    # ... register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(ticket_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    return app
```
