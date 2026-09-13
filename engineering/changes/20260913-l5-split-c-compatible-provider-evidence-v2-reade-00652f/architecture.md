# Architecture

Copy frozen contracts/provider/service, new v2 schema and all retention version hunks. Runtime takes only union/builder acceptance hunks, preserving old composition until D. Add V2 model registration and all four architecture/semantic catalog hunks. The reader-only persistence regression must use existing direct builder and SQLite fixtures, with synthetic v2 facts; no future HTTP/backup imports.
