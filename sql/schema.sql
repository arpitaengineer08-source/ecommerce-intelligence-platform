-- Layered warehouse:  raw (as-is CSV)  ->  staging (cleaned)  ->  analytics (star schema + model outputs)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;
