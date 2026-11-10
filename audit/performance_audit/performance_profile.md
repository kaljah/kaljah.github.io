# Performance Profiling Report

## 1. Executive Summary
Performance profiling was conducted on both the Python calculation engine and the SQLAlchemy/SQLite data layer.
Tested throughput on core calculation routines and database query/serialization overhead for multi-thousand record batches.

## 2. Calculation Engine Throughput (10,000 Operations)
| Calculator | Total Time (s) | Operations / Sec | Latency per Op (µs) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Stoichiometric Mass Balance** | 3.654 s | 2,736.7 ops/s | 365.4 µs | Excellent |
| **Flaring Dual-Efficiency** | 3.104 s | 3,221.7 ops/s | 310.4 µs | Excellent |
| **Calculation Dispatcher** | 8.2813 s | 1,207.5 ops/s | 828.13 µs | Good |

## 3. Database Layer Bottlenecks (Existing Database: 605 Scope 1, 121 Scope 2, 62 Scope 3 records)
- **Count Queries (`COUNT(*)` across all scopes)**: 0.2366 s
- **Fetch 5,000 ORM Records (`.limit(5000).all()`)**: 0.1166 s
- **Python Serialization of 5,000 Records to Dict**: 0.0162 s
- **Peak Memory Footprint**: 4.04 MB

## 4. Key Performance Bottlenecks Identified
1. **Unpaginated Exports**: `new/server/routes/reports_export.py` performs `q1.all()`, `q2.all()`, `q3.all()` loading the entire dataset into memory at once without chunking or streaming, consuming excessive memory on large datasets.
2. **Dynamic Recalculation on Export**: Flaring and venting exports recalculate emissions on the fly instead of reading stored precomputed rollups.
3. **Frontend Table Virtualization Missing**: In `new/client/src/pages/`, multiple data tables render large arrays without virtualization (`@tanstack/react-virtual`), causing DOM lag on datasets exceeding 500 rows.
