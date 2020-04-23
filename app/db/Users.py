from sqlalchemy import Table, Column, String, ForeignKey, DateTime, Enum, Boolean, ARRAY

from sqlalchemy.dialects.postgresql import UUID

from . import PermissionLevel, metadata

# Table of users - eg top level product users
users = Table(
    "users", metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, unique=True),
    Column("email", String(length=100), unique=True, nullable=False),
    Column("name", String(length=100)),
    Column("permission_level", Enum(PermissionLevel), nullable=False),
    Column("verified", Boolean),
    Column("phone_number", String(length=20)),
    Column("last_fetch", DateTime),
    Column("token", String()),
    Column("refresh_token", String()),
    Column("token_uri", String()),
    Column("client_id", String()),
    Column("client_secret", String()),
    Column("scopes", ARRAY(String()))
)
