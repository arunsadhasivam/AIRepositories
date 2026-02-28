-- ============================================================
-- IT Helpdesk Ticket System - Database Schema
-- Mock data for MCP AI Agent demo
-- ============================================================

-- Drop tables if they exist (clean setup)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS ticket_comments;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS agents;

-- ============================================================
-- Agents table (support staff - role-based access)
-- ============================================================
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'agent')),
    department VARCHAR(100)
);

INSERT INTO agents (username, full_name, role, department) VALUES
('admin_raj', 'Raj Kumar', 'admin', 'IT Operations'),
('agent_priya', 'Priya Sharma', 'agent', 'L1 Support'),
('agent_tom', 'Tom Wilson', 'agent', 'L2 Support'),
('agent_sara', 'Sara Lee', 'agent', 'L1 Support');

-- ============================================================
-- Employees table (people who raise tickets)
-- ============================================================
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    department VARCHAR(100),
    location VARCHAR(100)
);

INSERT INTO employees (full_name, email, department, location) VALUES
('Alice Johnson', 'alice@company.com', 'Finance', 'New York'),
('Bob Martin', 'bob@company.com', 'HR', 'Chicago'),
('Carol White', 'carol@company.com', 'Engineering', 'San Francisco'),
('David Lee', 'david@company.com', 'Sales', 'Austin'),
('Emma Davis', 'emma@company.com', 'Marketing', 'Boston'),
('Frank Miller', 'frank@company.com', 'Finance', 'New York'),
('Grace Kim', 'grace@company.com', 'Engineering', 'San Francisco'),
('Henry Brown', 'henry@company.com', 'HR', 'Chicago');

-- ============================================================
-- Tickets table (core entity)
-- ============================================================
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,       -- e.g. TKT-1001
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    category VARCHAR(50) CHECK (category IN ('hardware', 'software', 'network', 'access', 'other')),
    raised_by INTEGER REFERENCES employees(id),
    assigned_to INTEGER REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

INSERT INTO tickets (ticket_number, title, description, status, priority, category, raised_by, assigned_to, created_at, resolved_at) VALUES
('TKT-1001', 'Laptop not booting', 'Laptop shows black screen on startup after Windows update', 'open', 'high', 'hardware', 1, 2, NOW() - INTERVAL '3 days', NULL),
('TKT-1002', 'VPN not connecting', 'Cannot connect to office VPN from home since yesterday', 'in_progress', 'critical', 'network', 2, 3, NOW() - INTERVAL '1 day', NULL),
('TKT-1003', 'Access denied to SharePoint', 'Getting 403 error when accessing finance SharePoint folder', 'open', 'medium', 'access', 3, 2, NOW() - INTERVAL '5 days', NULL),
('TKT-1004', 'Outlook not syncing emails', 'Emails not syncing since this morning, tried restarting', 'resolved', 'medium', 'software', 4, 4, NOW() - INTERVAL '7 days', NOW() - INTERVAL '5 days'),
('TKT-1005', 'Printer offline in NY office', 'Floor 3 printer showing offline, multiple users affected', 'open', 'high', 'hardware', 1, 2, NOW() - INTERVAL '2 days', NULL),
('TKT-1006', 'Software license expired', 'Adobe Creative Cloud license expired, need renewal', 'in_progress', 'low', 'software', 5, 4, NOW() - INTERVAL '4 days', NULL),
('TKT-1007', 'New employee laptop setup', 'Need laptop provisioned for new joiner starting Monday', 'open', 'medium', 'hardware', 6, NULL, NOW() - INTERVAL '1 day', NULL),
('TKT-1008', 'Internet very slow in Chicago', 'Internet speed dropped significantly, whole floor affected', 'critical', 'critical', 'network', 7, 3, NOW() - INTERVAL '6 hours', NULL),
('TKT-1009', 'Password reset request', 'User locked out after too many failed attempts', 'resolved', 'low', 'access', 8, 4, NOW() - INTERVAL '10 days', NOW() - INTERVAL '9 days'),
('TKT-1010', 'Monitor flickering', 'Second monitor flickering randomly throughout the day', 'open', 'low', 'hardware', 3, NULL, NOW() - INTERVAL '8 days', NULL);

-- ============================================================
-- Ticket Comments table
-- ============================================================
CREATE TABLE ticket_comments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id),
    commented_by VARCHAR(100),
    comment TEXT NOT NULL,
    commented_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO ticket_comments (ticket_id, commented_by, comment, commented_at) VALUES
(1, 'agent_priya', 'Checked remotely - likely driver issue after update. Scheduling on-site visit.', NOW() - INTERVAL '2 days'),
(2, 'agent_tom', 'Escalated to network team. VPN server certificate may have expired.', NOW() - INTERVAL '18 hours'),
(5, 'agent_priya', 'Contacted printer vendor. Awaiting replacement part.', NOW() - INTERVAL '1 day'),
(8, 'agent_tom', 'ISP notified. Investigating bandwidth issue at Chicago data center.', NOW() - INTERVAL '4 hours');

-- ============================================================
-- Audit Logs table (every AI query gets logged - compliance)
-- ============================================================
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    queried_by VARCHAR(100) NOT NULL,        -- which agent/user ran the query
    natural_language_query TEXT NOT NULL,    -- what they asked in plain English
    generated_sql TEXT NOT NULL,             -- what SQL the AI generated
    executed_at TIMESTAMP DEFAULT NOW()
);
