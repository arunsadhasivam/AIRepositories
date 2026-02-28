#!/usr/bin/env python3
"""
MCP Server for IT Helpdesk Ticket System.

Connects an AI agent (Ollama) to a PostgreSQL helpdesk database.
Supports natural language querying, role-based access, and audit logging.
"""

import json
import asyncpg                                              # PostgreSQL async driver
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP                      # MCP framework
import logging

# ============================================================
# Server initialization
# ============================================================
mcp = FastMCP("helpdesk_mcp")                               # name must follow {service}_mcp pattern

# ============================================================
# Database configuration — update password to your local one
# ============================================================
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "help_desk",
    "user": "postgres",
    "password": "admin"                                  # ← change this
}

# ============================================================
# Pydantic input models (validated before hitting the DB)
# ============================================================

class QueryInput(BaseModel):
    """Input model for natural language ticket queries."""
    model_config = ConfigDict(
        str_strip_whitespace=True,                          # removes accidental spaces
        validate_assignment=True,
        extra="forbid"                                      # no unknown fields allowed
    )

    natural_query: str = Field(
        ...,
        description="Natural language question about tickets. E.g. 'Show all critical open tickets'",
        min_length=3,
        max_length=500
    )
    queried_by: str = Field(
        ...,
        description="Username of the agent making the query. E.g. 'agent_priya'",
        min_length=1,
        max_length=50
    )
    role: str = Field(
        ...,
        description="Role of the user: 'admin' or 'agent'",
        pattern="^(admin|agent)$"                          # only these two roles allowed
    )


class TicketStatusInput(BaseModel):
    """Input model for fetching a single ticket by number."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ticket_number: str = Field(
        ...,
        description="Ticket number to look up. E.g. 'TKT-1001'",
        pattern="^TKT-\\d+$"                              # must match TKT-XXXX format
    )
    queried_by: str = Field(..., description="Username of the agent", min_length=1)
    role: str = Field(..., description="Role: admin or agent", pattern="^(admin|agent)$")


class SummaryInput(BaseModel):
    """Input model for ticket summary statistics."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    queried_by: str = Field(..., description="Username of the agent", min_length=1)
    role: str = Field(..., description="Role: admin or agent", pattern="^(admin|agent)$")


# ============================================================
# Shared DB utility — single reusable connection function
# ============================================================

async def _get_db_connection() -> asyncpg.Connection:
    """Create and return a PostgreSQL connection."""
    conn = await asyncpg.connect(**DB_CONFIG)
    #await conn.execute("SET search_path TO help_desk")   # ← add this line
    return conn              # async connection using DB_CONFIG


async def _log_audit(conn: asyncpg.Connection, queried_by: str, natural_query: str, sql: str):
    """Log every query to audit_logs table for compliance tracking."""
    await conn.execute(
        """
        INSERT INTO audit_logs (queried_by, natural_language_query, generated_sql)
        VALUES ($1, $2, $3)
        """,
        queried_by, natural_query, sql                      # $1 $2 $3 are parameterized — safe from SQL injection
    )


def _apply_role_filter(base_sql: str, role: str) -> str:
    """
    Apply role-based access control to SQL query.
    Admin sees all tickets. Agent sees only assigned tickets.
    """
    if role == "agent":
        # wrap entire query as subquery to safely add WHERE
        return f"""
            SELECT * FROM ({base_sql}) AS filtered_tickets
            WHERE assigned_to IS NULL
        """
    return base_sql                                      # admin sees everything


def _handle_db_error(e: Exception) -> str:
    """Consistent, readable error messages for all DB failures."""
    if isinstance(e, asyncpg.PostgresError):
        return f"Database error: {str(e)}"
    if isinstance(e, asyncpg.TooManyConnectionsError):
        return "Error: Too many DB connections. Try again shortly."
    return f"Unexpected error: {type(e).__name__} — {str(e)}"


# ============================================================
# TOOL 1: Query tickets using natural language
# ============================================================

@mcp.tool(
    name="helpdesk_query_tickets",
    annotations={
        "title": "Query Helpdesk Tickets",
        "readOnlyHint": True,                               # this tool only reads, never writes
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def helpdesk_query_tickets(natural_query: str, queried_by: str, role: str) -> str:
    """
    Query helpdesk tickets using a natural language question.

    Translates the user's plain English question into a SQL query,
    runs it against the PostgreSQL helpdesk database, and returns results.
    Also logs the query to audit_logs for compliance.

    Args:
        params (QueryInput):
            - natural_query (str): Plain English question about tickets
            - queried_by (str): Username of person querying
            - role (str): 'admin' or 'agent'

    Returns:
        str: JSON-formatted list of matching tickets
    """
    conn = None
    try:
        # Step 1: Map natural language to SQL based on keywords
        q = natural_query.lower()                           # lowercase for easy matching

        # Build SQL based on what the user is asking
        if "critical" in q and "open" in q:
            logging.info(f'::::: CRITICAL OPEN TICKETS STATUS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, a.full_name AS assigned_to,
                       t.created_at
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                LEFT JOIN agents a ON t.assigned_to = a.id
                WHERE t.priority = 'critical' AND t.status = 'open'
                ORDER BY t.created_at DESC
            """
        elif "unassigned" in q:
            logging.info(f'::::: UNASSIGNED TICKETS STATUS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, t.created_at
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                WHERE t.assigned_to IS NULL
                ORDER BY t.created_at DESC
            """
        elif "network" in q:
            logging.info(f'::::: NETWORKS TICKETS STATUS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, a.full_name AS assigned_to
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                LEFT JOIN agents a ON t.assigned_to = a.id
                WHERE t.category = 'network'
                ORDER BY t.priority DESC
            """
        elif "open" in q:
            logging.info(f'::::: OPEN TICKETS STATUS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, a.full_name AS assigned_to
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                LEFT JOIN agents a ON t.assigned_to = a.id
                WHERE t.status = 'open'
                ORDER BY t.priority DESC
            """
        elif "resolved" in q:
            logging.info(f'::::: RESOLVED TICKETS STATUS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.status,
                       e.full_name AS raised_by, t.resolved_at
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                WHERE t.status = 'resolved'
                ORDER BY t.resolved_at DESC
            """
        elif "finance" in q or "hr" in q or "engineering" in q or "sales" in q:
            logging.info(f'::::: FINANCE (OR) HR (OR) ENGINEERING (OR) SALES TICKETS STATUS :::::')
            # department-based query
            dept = "Finance" if "finance" in q else \
                   "HR" if "hr" in q else \
                   "Engineering" if "engineering" in q else "Sales"
            sql = f"""
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, e.department
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                WHERE e.department = '{dept}'
                ORDER BY t.created_at DESC
            """
        else:
            # default: return all tickets (last 10)
            logging.info(f'::::: ALL TICKETS :::::')
            sql = """
                SELECT t.ticket_number, t.title, t.priority, t.status,
                       e.full_name AS raised_by, a.full_name AS assigned_to,
                       t.created_at
                FROM tickets t
                LEFT JOIN employees e ON t.raised_by = e.id
                LEFT JOIN agents a ON t.assigned_to = a.id
                ORDER BY t.created_at DESC
                LIMIT 10
            """

        # Step 2: Apply role-based filter
        sql = _apply_role_filter(sql, role)

        # Step 3: Connect to DB and execute
        conn = await _get_db_connection()
        rows = await conn.fetch(sql)                        # fetch returns list of Record objects

        # Step 4: Log the query for audit compliance
        await _log_audit(conn, queried_by, natural_query, sql)

        # Step 5: Convert rows to list of dicts for JSON output
        result = [dict(row) for row in rows]

        # Step 6: Handle empty results
        if not result:
            return json.dumps({"message": "No tickets found matching your query.", "count": 0})

        return json.dumps(result, indent=2, default=str)    # default=str handles datetime serialization

    except Exception as e:
        return _handle_db_error(e)

    finally:
        if conn:
            await conn.close()                              # always close connection


# ============================================================
# TOOL 2: Get single ticket by ticket number
# ============================================================

@mcp.tool(
    name="helpdesk_get_ticket",
    annotations={
        "title": "Get Ticket by Number",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def helpdesk_get_ticket(ticket_number: str, queried_by: str, role: str) -> str:
    """
    Fetch full details of a specific ticket including comments.

    Args:
        params (TicketStatusInput):
            - ticket_number (str): Ticket ID like 'TKT-1001'
            - queried_by (str): Username of person querying
            - role (str): 'admin' or 'agent'

    Returns:
        str: JSON with full ticket details and comments
    """
    conn = None
    try:
        sql = """
            SELECT t.ticket_number, t.title, t.description, t.status,
                   t.priority, t.category,
                   e.full_name AS raised_by, e.department,
                   a.full_name AS assigned_to,
                   t.created_at, t.updated_at, t.resolved_at
            FROM tickets t
            LEFT JOIN employees e ON t.raised_by = e.id
            LEFT JOIN agents a ON t.assigned_to = a.id
            WHERE t.ticket_number = $1
        """                                                 # $1 is parameterized — prevents SQL injection

        conn = await _get_db_connection()
        row = await conn.fetchrow(sql, ticket_number)

        if not row:
            return json.dumps({"error": f"Ticket {ticket_number} not found."})

        ticket = dict(row)

        comments_sql = """
            SELECT commented_by, comment, commented_at
            FROM ticket_comments
            WHERE ticket_id = (SELECT id FROM tickets WHERE ticket_number = $1)
            ORDER BY commented_at ASC
        """
        comments = await conn.fetch(comments_sql, ticket_number)
        ticket["comments"] = [dict(c) for c in comments]

        await _log_audit(conn, queried_by, f"Get ticket {ticket_number}", sql)

        return json.dumps(ticket, indent=2, default=str)

    except Exception as e:
        return _handle_db_error(e)

    finally:
        if conn:
            await conn.close()


# ============================================================
# TOOL 3: Get ticket summary statistics
# ============================================================

@mcp.tool(
    name="helpdesk_get_summary",
    annotations={
        "title": "Get Ticket Summary Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def helpdesk_get_summary(queried_by: str, role: str) -> str:
    """
    Returns a summary of ticket statistics — count by status and priority.
    Useful for dashboard-style overview queries.

    Args:
        params (SummaryInput):
            - queried_by (str): Username of the agent
            - role (str): 'admin' or 'agent'

    Returns:
        str: JSON with ticket counts grouped by status and priority
    """
    conn = None
    try:
        # Count tickets grouped by status
        status_sql = """
            SELECT status, COUNT(*) AS count
            FROM tickets
            GROUP BY status
            ORDER BY status
        """

        # Count tickets grouped by priority
        priority_sql = """
            SELECT priority, COUNT(*) AS count
            FROM tickets
            GROUP BY priority
            ORDER BY priority
        """

        # Count unassigned tickets
        unassigned_sql = """
            SELECT COUNT(*) AS unassigned_count
            FROM tickets
            WHERE assigned_to IS NULL AND status NOT IN ('resolved', 'closed')
        """

        conn = await _get_db_connection()

        # Run all 3 queries
        status_rows = await conn.fetch(status_sql)
        priority_rows = await conn.fetch(priority_sql)
        unassigned_row = await conn.fetchrow(unassigned_sql)

        summary = {
            "by_status": [dict(r) for r in status_rows],
            "by_priority": [dict(r) for r in priority_rows],
            "unassigned_open_tickets": dict(unassigned_row)["unassigned_count"]
        }

        # Audit log
        await _log_audit(conn, queried_by, "Get ticket summary", status_sql)

        return json.dumps(summary, indent=2, default=str)

    except Exception as e:
        return _handle_db_error(e)

    finally:
        if conn:
            await conn.close()


# ============================================================
# Entry point — run MCP server via stdio (for local use)
# ============================================================
if __name__ == "__main__":
    mcp.run()                                               # starts MCP server, listens on stdio