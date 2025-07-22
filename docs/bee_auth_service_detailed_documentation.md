# BeeConect Authentication Service - Detailed Documentation

## Overview

The BeeConect Authentication Service is a microservice responsible for user authentication and authorization within the BeeConect platform. It provides functionality for user registration, login, email verification, two-factor authentication, password reset, and token validation. The service is built using FastAPI, SQLAlchemy, and PostgreSQL, with additional integrations for RabbitMQ messaging, Redis caching, and Prometheus monitoring.

## Project Structure

The project follows a modular structure with clear separation of concerns:

```
bee_auth_services/
├── alembic/                  # Database migration scripts
├── docs/                     # Documentation files
├── events/                   # Event handling (RabbitMQ)
├── models/                   # Database models
├── routers/                  # API route definitions
├── schemas/                  # Pydantic schemas for validation
├── services/                 # Business logic services
├── tests/                    # Test suite
├── utils/                    # Utility functions
├── main.py                   # Application entry point
├── database.py               # Database connection setup
├── Dockerfile                # Container definition
└── pyproject.toml            # Project dependencies
```

## Core Files Explanation

### Main Application Files

#### `main.py`

The entry point for the FastAPI application. This file:
- Initializes the FastAPI application
- Configures middleware (CORS, security headers)
- Sets up rate limiting with Redis
- Configures Prometheus metrics
- Integrates Sentry for error tracking
- Defines basic health check endpoints
- Includes the authentication router

Key components:
- `lifespan` function: Manages application startup/shutdown, initializes Redis connection
- Exception handler: Captures and processes unhandled exceptions
- Health check endpoint: Provides service status information

#### `database.py`

Handles database connection and session management using SQLAlchemy. This file:
- Defines the database connection URL from environment variables
- Creates the SQLAlchemy engine and session factory
- Provides the Base class for model inheritance

#### `pyproject.toml`

Defines project metadata and dependencies using Poetry. Key dependencies include:
- FastAPI: Web framework
- SQLAlchemy: ORM for database operations
- Alembic: Database migration tool
- Passlib: Password hashing
- Python-jose: JWT token handling
- Aio-pika: RabbitMQ client
- Redis: For rate limiting and caching
- Prometheus: For metrics collection

### Models

#### `models/user.py`

Defines the User model for storing user account information:
- UUID primary key
- Email, hashed password, name, and contact information
- Role-based access control (client, admin_business, courier, collaborator, superadmin)
- Account status flags (active, email verified)
- Social login integration (provider, social ID)
- Timestamps for creation and updates

#### `models/email_verification.py`

Manages email verification tokens:
- Links to a user via foreign key
- Stores a unique verification token
- Includes expiration timestamp
- Tracks creation time

#### `models/twofa_tokens.py`

Handles two-factor authentication tokens:
- Links to a user via foreign key
- Stores authentication tokens
- Tracks token usage status
- Includes expiration timestamp
    - Records creation time

#### `models/password_reset_token.py`

Manages password reset tokens:
- Links to a user via foreign key
- Stores a secure reset token
- Includes expiration timestamp
- Tracks whether the token was used

#### `models/login_attempts.py`

Tracks login attempts for security monitoring:
- Records both successful and failed login attempts
- Stores IP address and user agent information
- Links to user account when possible
- Includes timestamp for when the attempt occurred

### Routers

#### `routers/auth.py`

Defines all authentication-related API endpoints:
- `/register`: User registration with email verification
- `/login`: User authentication with optional 2FA
- `/social-login` and `/social-callback`: Social media authentication
- `/verify-email`: Email verification endpoint
- `/verify-twofa`: Two-factor authentication verification
- `/validate`: Token validation endpoint
- `/request-reset`: Request password reset token
- `/reset-password`: Confirm password reset
- `/me`: Current user information retrieval

Each endpoint integrates with the appropriate services and models, implements rate limiting, and emits events when necessary.

### Services

#### `services/auth.py`

Implements core authentication business logic:
- `create_email_verification`: Generates email verification tokens
- `record_login_attempt`: Logs authentication attempts for security
- `create_twofa_token`: Creates two-factor authentication tokens

Constants define token expiration times:
- Email verification tokens: 15 minutes
- 2FA tokens: 5 minutes

#### `services/jwt.py`

Handles JWT token generation and validation:
- Supports both HMAC (HS256) and RSA (RS256) signing algorithms
- Implements token creation with user information and expiration
- Provides token validation and decoding
- Integrates with Redis for token caching
- Supports secret key rotation for security

### Schemas

#### `schemas/user.py`

Defines Pydantic models for request/response validation:
- `UserCreate`: Registration request validation
- `UserLogin`: Login credentials validation
- `UserRead`: User information response format
- `SocialLogin`: Social authentication data validation
- `TwoFAVerify`: Two-factor verification request validation

#### `schemas/event.py`

Defines event structures for RabbitMQ messaging:
- `UserRegisteredEvent`: Emitted when a user registers
- `UserLoggedInEvent`: Emitted on successful login
- `EmailVerificationSentEvent`: Tracks email verification
- `TwoFARequestedEvent`: Signals 2FA initiation
- `PasswordResetRequestedEvent`: Emitted when a user requests password reset

### Events

#### `events/rabbitmq.py`

Handles asynchronous messaging with RabbitMQ:
- Establishes connection to RabbitMQ server
- Defines exchange and queue configuration
- Implements event emission functionality
- Provides structured event publishing

### Utils

#### `utils/security.py`

Implements security-related utilities:
- Password hashing and verification using bcrypt
- Security header configuration
- Input validation and sanitization

#### `utils/token_store.py`

Manages token caching in Redis:
- Stores tokens with expiration
- Retrieves cached tokens
- Handles token invalidation

#### `utils/logging.py`

Configures structured logging:
- Sets up JSON log formatting
- Configures log levels based on environment
- Implements request ID tracking

#### `utils/metrics.py`

Implements Prometheus metrics collection:
- Tracks authentication success/failure rates
- Monitors API endpoint performance
- Records error counts

#### `utils/alerts.py`

Handles alerting for critical issues:
- Integrates with monitoring systems
- Triggers alerts for security events
- Processes threshold-based notifications

## Database Migrations

### `alembic/`

Contains database migration scripts:
- `env.py`: Configures the migration environment
- `versions/`: Contains individual migration scripts
  - `1c572a13dc24_create_auth_tables.py`: Initial schema creation
  - `35b6c0f1d431_update_login_attempts.py`: Updates to login tracking

## Testing

### `tests/`

Comprehensive test suite covering:
- Authentication flows (registration, login)
- Email verification process
- Two-factor authentication
- Token validation
- Password reset flow
- Security features (CORS, headers)
- Event emission
- Rate limiting
- Metrics collection

## Configuration

The service is configured through environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key
- `REDIS_HOST`, `REDIS_PORT`: Redis connection
- `RABBITMQ_URL`: RabbitMQ connection
- `CORS_ORIGINS`: Allowed origins for CORS
- `ENVIRONMENT`: Runtime environment (development/production)
- `SENTRY_DSN`: Sentry error tracking

## Deployment

### `Dockerfile`

Defines the container image for deployment:
- Uses Python 3.12 base image
- Installs Poetry and dependencies
- Configures the application for production
- Sets up health checks
- Exposes the service port

## Security Features

The service implements multiple security measures:
- Password hashing with bcrypt
- JWT-based authentication
- Rate limiting to prevent brute force attacks
- Login attempt tracking
- Two-factor authentication
- Email verification
- Password reset tokens
- Security headers (HSTS, CSP, etc.)
- Secret key rotation support

## Integration Points

The service integrates with several external systems:
- PostgreSQL: Primary data storage
- Redis: Rate limiting and token caching
- RabbitMQ: Event messaging
- Prometheus: Metrics collection
- Sentry: Error tracking

## Conclusion

The BeeConect Authentication Service provides a secure, scalable authentication solution for the BeeConect platform. Its modular design allows for easy maintenance and extension, while its comprehensive security features ensure user data protection.